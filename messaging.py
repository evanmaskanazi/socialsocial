"""
Messaging module for Thera Social
Handles private messaging between users
"""
from datetime import datetime, timedelta
from sqlalchemy import or_, and_, desc

class MessagingManager:
    """Manages private messaging between users"""
    
    def __init__(self, db, redis_client, security_manager):
        self.db = db
        self.redis = redis_client
        self.security = security_manager
        
    def send_message(self, sender_id, recipient_id, content):
        """Send private message to another user"""
        from models import PrivateMessage, User
        from security import encrypt_field
        
        # Validate users exist
        sender = User.query.get(sender_id)
        recipient = User.query.get(recipient_id)
        
        if not sender or not recipient:
            raise ValueError("Invalid sender or recipient")
        
        # Check if users are allowed to message
        if not self._can_send_message(sender_id, recipient_id):
            raise ValueError("Users must be mutual followers to exchange messages")
        
        # Check for spam
        if self._is_spam(sender_id, content):
            raise ValueError("Message appears to be spam")
        
        # Create message
        message = PrivateMessage(
            sender_id=sender_id,
            recipient_id=recipient_id,
            content_encrypted=encrypt_field(content)
        )
        
        self.db.session.add(message)
        
        try:
            self.db.session.commit()
            
            # Send notification
            self._send_message_notification(sender, recipient, message.id)
            
            # Update conversation cache
            self._update_conversation_cache(sender_id, recipient_id)
            
            return message.id
            
        except Exception as e:
            self.db.session.rollback()
            raise e
    
    def get_conversation(self, user_id, other_user_id, page=1, per_page=20):
        """Get conversation between two users"""
        from models import PrivateMessage, User
        from security import decrypt_field
        
        # Get messages between users
        query = PrivateMessage.query.filter(
            or_(
                and_(
                    PrivateMessage.sender_id == user_id,
                    PrivateMessage.recipient_id == other_user_id,
                    PrivateMessage.is_deleted_sender == False
                ),
                and_(
                    PrivateMessage.sender_id == other_user_id,
                    PrivateMessage.recipient_id == user_id,
                    PrivateMessage.is_deleted_recipient == False
                )
            )
        ).order_by(desc(PrivateMessage.sent_at))
        
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        messages = []
        for msg in paginated.items:
            # Mark as read if recipient
            if msg.recipient_id == user_id and not msg.is_read:
                msg.is_read = True
            
            sender = User.query.get(msg.sender_id)
            
            messages.append({
                'id': msg.id,
                'sender': {
                    'id': sender.anonymous_id,
                    'display_name': sender.display_name
                },
                'content': decrypt_field(msg.content_encrypted),
                'is_own': msg.sender_id == user_id,
                'is_read': msg.is_read,
                'sent_at': msg.sent_at.isoformat()
            })
        
        # Commit read status updates
        try:
            self.db.session.commit()
        except Exception:
            self.db.session.rollback()
        
        # Reverse messages for chronological order in UI
        messages.reverse()
        
        return {
            'messages': messages,
            'pagination': {
                'page': paginated.page,
                'pages': paginated.pages,
                'total': paginated.total,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        }
    
    def get_conversations_list(self, user_id, page=1, per_page=20):
        """Get list of user's conversations"""
        from models import PrivateMessage, User
        from security import decrypt_field
        from sqlalchemy import case, func
        
        # Get unique conversation partners with latest message
        subquery = self.db.session.query(
            case(
                (PrivateMessage.sender_id == user_id, PrivateMessage.recipient_id),
                else_=PrivateMessage.sender_id
            ).label('other_user_id'),
            func.max(PrivateMessage.sent_at).label('last_message_time')
        ).filter(
            or_(
                and_(
                    PrivateMessage.sender_id == user_id,
                    PrivateMessage.is_deleted_sender == False
                ),
                and_(
                    PrivateMessage.recipient_id == user_id,
                    PrivateMessage.is_deleted_recipient == False
                )
            )
        ).group_by('other_user_id').subquery()
        
        # Get conversations with user details
        conversations = self.db.session.query(
            subquery.c.other_user_id,
            subquery.c.last_message_time,
            User
        ).join(
            User,
            User.id == subquery.c.other_user_id
        ).order_by(
            desc(subquery.c.last_message_time)
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        result = []
        for other_id, last_time, other_user in conversations.items:
            # Get last message
            last_message = PrivateMessage.query.filter(
                or_(
                    and_(
                        PrivateMessage.sender_id == user_id,
                        PrivateMessage.recipient_id == other_id
                    ),
                    and_(
                        PrivateMessage.sender_id == other_id,
                        PrivateMessage.recipient_id == user_id
                    )
                )
            ).order_by(desc(PrivateMessage.sent_at)).first()
            
            # Count unread messages
            unread_count = PrivateMessage.query.filter(
                PrivateMessage.sender_id == other_id,
                PrivateMessage.recipient_id == user_id,
                PrivateMessage.is_read == False
            ).count()
            
            result.append({
                'user': {
                    'id': other_user.anonymous_id,
                    'display_name': other_user.display_name
                },
                'last_message': {
                    'content': decrypt_field(last_message.content_encrypted)[:100] if last_message else None,
                    'sent_at': last_message.sent_at.isoformat() if last_message else None,
                    'is_own': last_message.sender_id == user_id if last_message else False
                },
                'unread_count': unread_count
            })
        
        return {
            'conversations': result,
            'pagination': {
                'page': conversations.page,
                'pages': conversations.pages,
                'total': conversations.total
            }
        }
    
    def delete_message(self, user_id, message_id):
        """Delete message for user"""
        from models import PrivateMessage
        
        message = PrivateMessage.query.get(message_id)
        
        if not message:
            return False
        
        # Check ownership
        if message.sender_id == user_id:
            message.is_deleted_sender = True
        elif message.recipient_id == user_id:
            message.is_deleted_recipient = True
        else:
            return False
        
        # If both deleted, actually delete
        if message.is_deleted_sender and message.is_deleted_recipient:
            self.db.session.delete(message)
        
        try:
            self.db.session.commit()
            return True
        except Exception:
            self.db.session.rollback()
            return False
    
    def delete_conversation(self, user_id, other_user_id):
        """Delete entire conversation for user"""
        from models import PrivateMessage
        
        # Mark all messages as deleted for user
        messages = PrivateMessage.query.filter(
            or_(
                and_(
                    PrivateMessage.sender_id == user_id,
                    PrivateMessage.recipient_id == other_user_id
                ),
                and_(
                    PrivateMessage.sender_id == other_user_id,
                    PrivateMessage.recipient_id == user_id
                )
            )
        ).all()
        
        for message in messages:
            if message.sender_id == user_id:
                message.is_deleted_sender = True
            if message.recipient_id == user_id:
                message.is_deleted_recipient = True
            
            # If both deleted, actually delete
            if message.is_deleted_sender and message.is_deleted_recipient:
                self.db.session.delete(message)
        
        try:
            self.db.session.commit()
            
            # Clear conversation cache
            self._clear_conversation_cache(user_id, other_user_id)
            
            return True
            
        except Exception:
            self.db.session.rollback()
            return False
    
    def get_unread_count(self, user_id):
        """Get total unread message count"""
        from models import PrivateMessage
        
        count = PrivateMessage.query.filter(
            PrivateMessage.recipient_id == user_id,
            PrivateMessage.is_read == False,
            PrivateMessage.is_deleted_recipient == False
        ).count()
        
        # Cache the count
        cache_key = f"unread_messages:{user_id}"
        self.redis.setex(cache_key, 300, count)  # 5 minutes
        
        return count
    
    def mark_conversation_read(self, user_id, other_user_id):
        """Mark all messages in conversation as read"""
        from models import PrivateMessage
        
        messages = PrivateMessage.query.filter(
            PrivateMessage.sender_id == other_user_id,
            PrivateMessage.recipient_id == user_id,
            PrivateMessage.is_read == False
        ).all()
        
        for message in messages:
            message.is_read = True
        
        try:
            self.db.session.commit()
            
            # Clear unread cache
            cache_key = f"unread_messages:{user_id}"
            self.redis.delete(cache_key)
            
            return True
            
        except Exception:
            self.db.session.rollback()
            return False
    
    def search_messages(self, user_id, query, page=1, per_page=20):
        """Search messages for user"""
        from models import PrivateMessage, User
        from security import decrypt_field
        
        if len(query) < 3:
            return {'messages': [], 'pagination': {}}
        
        # Get all messages for user
        messages = PrivateMessage.query.filter(
            or_(
                and_(
                    PrivateMessage.sender_id == user_id,
                    PrivateMessage.is_deleted_sender == False
                ),
                and_(
                    PrivateMessage.recipient_id == user_id,
                    PrivateMessage.is_deleted_recipient == False
                )
            )
        ).order_by(desc(PrivateMessage.sent_at)).all()
        
        # Search in decrypted content
        matching_messages = []
        query_lower = query.lower()
        
        for message in messages:
            content = decrypt_field(message.content_encrypted)
            if content and query_lower in content.lower():
                matching_messages.append(message)
        
        # Paginate results manually
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_messages = matching_messages[start_idx:end_idx]
        
        # Format results
        results = []
        for msg in page_messages:
            sender = User.query.get(msg.sender_id)
            recipient = User.query.get(msg.recipient_id)
            
            results.append({
                'id': msg.id,
                'sender': {
                    'id': sender.anonymous_id,
                    'display_name': sender.display_name
                },
                'recipient': {
                    'id': recipient.anonymous_id,
                    'display_name': recipient.display_name
                },
                'content': decrypt_field(msg.content_encrypted),
                'sent_at': msg.sent_at.isoformat()
            })
        
        total_pages = (len(matching_messages) + per_page - 1) // per_page
        
        return {
            'messages': results,
            'pagination': {
                'page': page,
                'pages': total_pages,
                'total': len(matching_messages)
            }
        }
    
    def _can_send_message(self, sender_id, recipient_id):
        """Check if users can exchange messages"""
        from models import Follow
        
        # Check mutual following
        follow1 = Follow.query.filter_by(
            follower_id=sender_id,
            followed_id=recipient_id
        ).first()
        
        follow2 = Follow.query.filter_by(
            follower_id=recipient_id,
            followed_id=sender_id
        ).first()
        
        return bool(follow1 and follow2)
    
    def _is_spam(self, sender_id, content):
        """Check if message appears to be spam"""
        # Check message rate
        rate_key = f"message_rate:{sender_id}"
        current_count = self.redis.incr(rate_key)
        
        if current_count == 1:
            self.redis.expire(rate_key, 60)  # 1 minute window
        
        if current_count > 10:  # More than 10 messages per minute
            return True
        
        # Check for spam patterns
        spam_patterns = [
            r'(viagra|cialis|pharmacy)',
            r'(click here|buy now|limited time)',
            r'(make money|work from home|mlm)',
            r'(http|https)://[^\s]+(\.tk|\.ml|\.ga)',  # Suspicious domains
            r'(\$\d+|€\d+|£\d+)',  # Money amounts
            r'(100% free|guaranteed|no risk)'
        ]
        
        import re
        content_lower = content.lower()
        
        for pattern in spam_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return True
        
        # Check for repetition (same message multiple times)
        recent_key = f"recent_messages:{sender_id}"
        message_hash = hash(content)
        
        recent_hashes = self.redis.lrange(recent_key, 0, -1)
        if str(message_hash).encode() in recent_hashes:
            return True  # Duplicate message
        
        self.redis.lpush(recent_key, message_hash)
        self.redis.ltrim(recent_key, 0, 9)  # Keep last 10
        self.redis.expire(recent_key, 300)  # 5 minutes
        
        return False
    
    def _send_message_notification(self, sender, recipient, message_id):
        """Send notification for new message"""
        from models import Alert
        from security import encrypt_field
        
        # Create in-app alert
        alert = Alert(
            user_id=recipient.id,
            alert_type='new_message',
            title=f"New message from {sender.display_name}",
            message_encrypted=encrypt_field(f"You have a new message from {sender.display_name}"),
            priority='medium'
        )
        
        self.db.session.add(alert)
        
        try:
            self.db.session.commit()
            
            # Send real-time notification
            self._send_realtime_notification(recipient.id, 'new_message', {
                'sender_id': sender.anonymous_id,
                'sender_name': sender.display_name,
                'message_id': message_id
            })
            
        except Exception:
            self.db.session.rollback()
    
    def _send_realtime_notification(self, user_id, notification_type, data):
        """Send real-time notification through Redis pub/sub"""
        channel = f"notifications:{user_id}"
        
        message = {
            'type': notification_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.redis.publish(channel, str(message))
    
    def _update_conversation_cache(self, user1_id, user2_id):
        """Update conversation cache"""
        # Clear cache for both users
        cache_keys = [
            f"conversation:{user1_id}:{user2_id}",
            f"conversation:{user2_id}:{user1_id}",
            f"conversations_list:{user1_id}",
            f"conversations_list:{user2_id}"
        ]
        
        for key in cache_keys:
            self.redis.delete(key)
    
    def _clear_conversation_cache(self, user1_id, user2_id):
        """Clear conversation cache"""
        self._update_conversation_cache(user1_id, user2_id)
    
    def get_message_statistics(self, user_id):
        """Get messaging statistics for user"""
        from models import PrivateMessage
        from sqlalchemy import func
        
        # Total messages sent
        sent_count = PrivateMessage.query.filter_by(
            sender_id=user_id,
            is_deleted_sender=False
        ).count()
        
        # Total messages received
        received_count = PrivateMessage.query.filter_by(
            recipient_id=user_id,
            is_deleted_recipient=False
        ).count()
        
        # Unique conversation partners
        sent_to = self.db.session.query(
            func.count(func.distinct(PrivateMessage.recipient_id))
        ).filter(
            PrivateMessage.sender_id == user_id
        ).scalar()
        
        received_from = self.db.session.query(
            func.count(func.distinct(PrivateMessage.sender_id))
        ).filter(
            PrivateMessage.recipient_id == user_id
        ).scalar()
        
        unique_partners = max(sent_to or 0, received_from or 0)
        
        # Average response time
        response_times = []
        
        # Get conversations where user responded
        responses = PrivateMessage.query.filter_by(
            sender_id=user_id
        ).order_by(PrivateMessage.sent_at).all()
        
        for response in responses:
            # Find the message this is responding to
            previous = PrivateMessage.query.filter(
                PrivateMessage.sender_id == response.recipient_id,
                PrivateMessage.recipient_id == user_id,
                PrivateMessage.sent_at < response.sent_at
            ).order_by(desc(PrivateMessage.sent_at)).first()
            
            if previous:
                time_diff = (response.sent_at - previous.sent_at).total_seconds()
                if time_diff < 86400:  # Only count if less than 24 hours
                    response_times.append(time_diff)
        
        avg_response_time = None
        if response_times:
            avg_seconds = sum(response_times) / len(response_times)
            if avg_seconds < 3600:
                avg_response_time = f"{int(avg_seconds / 60)} minutes"
            else:
                avg_response_time = f"{int(avg_seconds / 3600)} hours"
        
        return {
            'messages_sent': sent_count,
            'messages_received': received_count,
            'unique_conversations': unique_partners,
            'average_response_time': avg_response_time
        }
    
    def report_message(self, reporter_id, message_id, reason):
        """Report a message for violation"""
        from models import PrivateMessage, Report
        from security import encrypt_field
        
        message = PrivateMessage.query.get(message_id)
        
        if not message:
            return False
        
        # Verify reporter is recipient
        if message.recipient_id != reporter_id:
            return False
        
        # Create report
        report = Report(
            reporter_id=reporter_id,
            reported_user_id=message.sender_id,
            violation_type='inappropriate_message',
            description_encrypted=encrypt_field(reason),
            evidence={'message_id': message_id},
            status='pending'
        )
        
        self.db.session.add(report)
        
        try:
            self.db.session.commit()
            return True
        except Exception:
            self.db.session.rollback()
            return False
