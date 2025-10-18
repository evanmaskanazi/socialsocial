"""
Social features module for Thera Social
Handles following, circles, feeds, and social interactions
"""
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, desc
from security import decrypt_field, encrypt_field

class SocialManager:
    """Manages social features and interactions"""
    
    def __init__(self, db, redis_client):
        self.db = db
        self.redis = redis_client
        
    def follow_user(self, follower_id, followed_id):
        """Follow another user"""
        from models import Follow, User
        
        # Check if already following
        existing = Follow.query.filter_by(
            follower_id=follower_id,
            followed_id=followed_id
        ).first()
        
        if existing:
            return False
        
        # Create follow relationship
        follow = Follow(
            follower_id=follower_id,
            followed_id=followed_id
        )
        
        self.db.session.add(follow)
        
        try:
            self.db.session.commit()
            
            # Clear cache
            self._clear_follow_cache(follower_id)
            self._clear_follow_cache(followed_id)
            
            # Update follower counts in cache
            self._update_follow_counts(follower_id, followed_id)
            
            return True
            
        except Exception as e:
            self.db.session.rollback()
            return False
    
    def unfollow_user(self, follower_id, followed_id):
        """Unfollow a user"""
        from models import Follow, CircleMember, Circle
        
        follow = Follow.query.filter_by(
            follower_id=follower_id,
            followed_id=followed_id
        ).first()
        
        if not follow:
            return False
        
        # Remove from all circles
        CircleMember.query.filter(
            CircleMember.circle_id.in_(
                self.db.session.query(Circle.id).filter_by(user_id=follower_id)
            ),
            CircleMember.user_id == followed_id
        ).delete()
        
        # Remove follow
        self.db.session.delete(follow)
        
        try:
            self.db.session.commit()
            
            # Clear cache
            self._clear_follow_cache(follower_id)
            self._clear_follow_cache(followed_id)
            
            # Update follower counts
            self._update_follow_counts(follower_id, followed_id)
            
            return True
            
        except Exception:
            self.db.session.rollback()
            return False
    
    def get_user_circles(self, user_id):
        """Get user's circles with members"""
        from models import Circle, CircleMember, User
        
        circles = Circle.query.filter_by(user_id=user_id).all()
        
        result = []
        for circle in circles:
            members = []
            
            for member in circle.members:
                user = User.query.get(member.user_id)
                if user:
                    members.append({
                        'id': user.anonymous_id,
                        'display_name': user.display_name,
                        'added_at': member.added_at.isoformat()
                    })
            
            result.append({
                'id': circle.id,
                'name': circle.name,
                'type': circle.circle_type,
                'members': members,
                'member_count': len(members)
            })
        
        return result
    
    def add_to_circle(self, circle_id, user_id):
        """Add user to circle"""
        from models import Circle, CircleMember
        
        # Check if circle exists
        circle = Circle.query.get(circle_id)
        if not circle:
            return False
        
        # Check if already in circle
        existing = CircleMember.query.filter_by(
            circle_id=circle_id,
            user_id=user_id
        ).first()
        
        if existing:
            return False
        
        # Add to circle
        member = CircleMember(
            circle_id=circle_id,
            user_id=user_id
        )
        
        self.db.session.add(member)
        
        try:
            self.db.session.commit()
            return True
        except Exception:
            self.db.session.rollback()
            return False
    
    def remove_from_circle(self, circle_id, user_id):
        """Remove user from circle"""
        from models import CircleMember
        
        member = CircleMember.query.filter_by(
            circle_id=circle_id,
            user_id=user_id
        ).first()
        
        if not member:
            return False
        
        self.db.session.delete(member)
        
        try:
            self.db.session.commit()
            return True
        except Exception:
            self.db.session.rollback()
            return False
    
    def get_user_feed(self, user_id, page=1, per_page=20):
        """Get personalized feed for user"""
        from models import Post, User, Follow, CircleMember, Circle
        
        # Get users this person follows
        following = Follow.query.filter_by(follower_id=user_id).all()
        following_ids = [f.followed_id for f in following]
        
        # Include own posts
        following_ids.append(user_id)
        
        # Build query for visible posts
        query = Post.query.filter(
            Post.user_id.in_(following_ids),
            Post.is_deleted == False
        )
        
        # Filter by visibility
        visibility_filters = []
        
        # Public/general posts
        visibility_filters.append(Post.visibility == 'general')
        
        # Posts in circles user belongs to
        user_circles = CircleMember.query.filter_by(user_id=user_id).all()
        circle_ids = [c.circle_id for c in user_circles]
        
        if circle_ids:
            visibility_filters.append(
                and_(
                    Post.visibility.in_(['family', 'close_friends']),
                    Post.circle_id.in_(circle_ids)
                )
            )
        
        # Own private posts
        visibility_filters.append(
            and_(
                Post.visibility == 'private',
                Post.user_id == user_id
            )
        )
        
        query = query.filter(or_(*visibility_filters))
        
        # Order by created date
        query = query.order_by(desc(Post.created_at))
        
        # Paginate
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Format posts
        posts = []
        for post in paginated.items:
            author = User.query.get(post.user_id)
            
            posts.append({
                'id': post.id,
                'author': {
                    'id': author.anonymous_id,
                    'display_name': author.display_name
                },
                'content': decrypt_field(post.content_encrypted),
                'visibility': post.visibility,
                'created_at': post.created_at.isoformat(),
                'is_own': post.user_id == user_id
            })
        
        return {
            'posts': posts,
            'pagination': {
                'page': paginated.page,
                'pages': paginated.pages,
                'total': paginated.total,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        }
    
    def get_followers(self, user_id, page=1, per_page=20):
        """Get user's followers"""
        from models import Follow, User
        
        query = Follow.query.filter_by(followed_id=user_id)
        query = query.order_by(desc(Follow.created_at))
        
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        followers = []
        for follow in paginated.items:
            user = User.query.get(follow.follower_id)
            if user:
                followers.append({
                    'id': user.anonymous_id,
                    'display_name': user.display_name,
                    'followed_at': follow.created_at.isoformat()
                })
        
        return {
            'followers': followers,
            'pagination': {
                'page': paginated.page,
                'pages': paginated.pages,
                'total': paginated.total
            }
        }
    
    def get_following(self, user_id, page=1, per_page=20):
        """Get users that user follows"""
        from models import Follow, User
        
        query = Follow.query.filter_by(follower_id=user_id)
        query = query.order_by(desc(Follow.created_at))
        
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        following = []
        for follow in paginated.items:
            user = User.query.get(follow.followed_id)
            if user:
                following.append({
                    'id': user.anonymous_id,
                    'display_name': user.display_name,
                    'followed_at': follow.created_at.isoformat()
                })
        
        return {
            'following': following,
            'pagination': {
                'page': paginated.page,
                'pages': paginated.pages,
                'total': paginated.total
            }
        }
    
    def can_message(self, user1_id, user2_id):
        """Check if two users can message (mutual followers)"""
        from models import Follow
        
        # Check both directions
        follow1 = Follow.query.filter_by(
            follower_id=user1_id,
            followed_id=user2_id
        ).first()
        
        follow2 = Follow.query.filter_by(
            follower_id=user2_id,
            followed_id=user1_id
        ).first()
        
        return bool(follow1 and follow2)
    
    def alert_followers(self, user_id, parameter_name, trend_data):
        """Alert followers about significant changes"""
        from models import Follow, User, Alert, Circle, CircleMember
        
        user = User.query.get(user_id)
        if not user:
            return
        
        # Determine alert priority based on change
        change_percent = abs(trend_data.get('change_percent', 0))
        
        if change_percent > 50:
            priority = 'high'
        elif change_percent > 30:
            priority = 'medium'
        else:
            priority = 'low'
        
        # Get followers who should be alerted
        followers = Follow.query.filter_by(followed_id=user_id).all()
        
        # For sensitive parameters, only alert close circles
        sensitive_params = ['mood', 'anxiety', 'depression']
        
        if parameter_name.lower() in sensitive_params:
            # Only alert family and close friends
            close_circles = Circle.query.filter(
                Circle.user_id == user_id,
                Circle.circle_type.in_(['family', 'close_friends'])
            ).all()
            
            close_member_ids = set()
            for circle in close_circles:
                members = CircleMember.query.filter_by(circle_id=circle.id).all()
                close_member_ids.update([m.user_id for m in members])
            
            # Filter followers to only close connections
            follower_ids = [f.follower_id for f in followers if f.follower_id in close_member_ids]
        else:
            follower_ids = [f.follower_id for f in followers]
        
        # Create alerts for followers
        message = f"{user.display_name}'s {parameter_name} has changed significantly"
        
        if trend_data.get('trend_type') == 'decreasing' and parameter_name.lower() in ['mood', 'energy']:
            message += " - they might need support"
            priority = 'high'
        
        for follower_id in follower_ids:
            alert = Alert(
                user_id=follower_id,
                alert_type='follower_trend_change',
                title=f"Update from {user.display_name}",
                message_encrypted=encrypt_field(message),
                priority=priority
            )
            self.db.session.add(alert)
        
        try:
            self.db.session.commit()
        except Exception:
            self.db.session.rollback()
    
    def search_users(self, query, user_id, page=1, per_page=20):
        """Search for users by display name"""
        from models import User, Follow
        
        if len(query) < 3:
            return {'users': [], 'pagination': {}}
        
        # Search by display name (case-insensitive)
        search_query = User.query.filter(
            User.display_name.ilike(f'%{query}%'),
            User.is_active == True,
            User.id != user_id  # Exclude self
        )
        
        paginated = search_query.paginate(page=page, per_page=per_page, error_out=False)
        
        users = []
        for user in paginated.items:
            # Check if following
            is_following = Follow.query.filter_by(
                follower_id=user_id,
                followed_id=user.id
            ).first() is not None
            
            users.append({
                'id': user.anonymous_id,
                'display_name': user.display_name,
                'is_following': is_following
            })
        
        return {
            'users': users,
            'pagination': {
                'page': paginated.page,
                'pages': paginated.pages,
                'total': paginated.total
            }
        }
    
    def get_user_stats(self, user_id):
        """Get user's social statistics"""
        from models import Follow, Post, Parameter
        
        stats = {
            'followers_count': Follow.query.filter_by(followed_id=user_id).count(),
            'following_count': Follow.query.filter_by(follower_id=user_id).count(),
            'posts_count': Post.query.filter_by(user_id=user_id, is_deleted=False).count(),
            'parameters_count': Parameter.query.filter_by(user_id=user_id, is_active=True).count()
        }
        
        # Cache stats
        cache_key = f"user_stats:{user_id}"
        self.redis.setex(cache_key, 300, str(stats))  # 5 minutes
        
        return stats
    
    def get_trending_topics(self, days=7):
        """Get trending topics from posts"""
        from models import Post
        import re
        from collections import Counter
        
        # Get recent posts
        since = datetime.utcnow() - timedelta(days=days)
        posts = Post.query.filter(
            Post.created_at >= since,
            Post.is_deleted == False
        ).all()
        
        # Extract hashtags and common words
        hashtags = Counter()
        words = Counter()
        
        for post in posts:
            content = decrypt_field(post.content_encrypted)
            if content:
                # Find hashtags
                tags = re.findall(r'#\w+', content)
                hashtags.update(tags)
                
                # Find common words (exclude common stop words)
                stop_words = {'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'as', 'are', 'was', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'could', 'to', 'of', 'in', 'for', 'with', 'that', 'this', 'it', 'i', 'you', 'we', 'they', 'he', 'she'}
                
                word_list = re.findall(r'\b[a-z]+\b', content.lower())
                meaningful_words = [w for w in word_list if len(w) > 3 and w not in stop_words]
                words.update(meaningful_words)
        
        return {
            'hashtags': hashtags.most_common(10),
            'topics': words.most_common(10)
        }
    
    def _clear_follow_cache(self, user_id):
        """Clear follow-related cache for user"""
        cache_keys = [
            f"user_stats:{user_id}",
            f"followers:{user_id}",
            f"following:{user_id}"
        ]
        
        for key in cache_keys:
            self.redis.delete(key)
    
    def _update_follow_counts(self, follower_id, followed_id):
        """Update follow counts in cache"""
        from models import Follow
        
        # Update follower's following count
        following_count = Follow.query.filter_by(follower_id=follower_id).count()
        self.redis.setex(f"following_count:{follower_id}", 300, following_count)
        
        # Update followed's follower count
        follower_count = Follow.query.filter_by(followed_id=followed_id).count()
        self.redis.setex(f"follower_count:{followed_id}", 300, follower_count)
    
    def recommend_users(self, user_id, limit=10):
        """Recommend users to follow"""
        from models import User, Follow, CircleMember
        from sqlalchemy import func
        
        # Get users the current user follows
        following = Follow.query.filter_by(follower_id=user_id).all()
        following_ids = [f.followed_id for f in following]
        
        # Get users followed by people you follow (collaborative filtering)
        recommendations = {}
        
        for followed_id in following_ids:
            # Get who they follow
            their_following = Follow.query.filter_by(follower_id=followed_id).all()
            
            for f in their_following:
                if f.followed_id != user_id and f.followed_id not in following_ids:
                    if f.followed_id not in recommendations:
                        recommendations[f.followed_id] = 0
                    recommendations[f.followed_id] += 1
        
        # Sort by frequency
        sorted_recs = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        # Get user details
        recommended_users = []
        for rec_user_id, score in sorted_recs:
            user = User.query.get(rec_user_id)
            if user and user.is_active:
                recommended_users.append({
                    'id': user.anonymous_id,
                    'display_name': user.display_name,
                    'mutual_connections': score
                })
        
        return recommended_users
    
    def get_mutual_followers(self, user1_id, user2_id):
        """Get mutual followers between two users"""
        from models import Follow, User
        
        # Get followers of both users
        user1_followers = set([f.follower_id for f in Follow.query.filter_by(followed_id=user1_id).all()])
        user2_followers = set([f.follower_id for f in Follow.query.filter_by(followed_id=user2_id).all()])
        
        # Find intersection
        mutual = user1_followers.intersection(user2_followers)
        
        # Get user details
        mutual_users = []
        for user_id in mutual:
            user = User.query.get(user_id)
            if user:
                mutual_users.append({
                    'id': user.anonymous_id,
                    'display_name': user.display_name
                })
        
        return mutual_users
    
    def get_circle_feed(self, user_id, circle_type, page=1, per_page=20):
        """Get posts from a specific circle"""
        from models import Post, User, Circle, CircleMember
        
        # Get the circle
        circle = Circle.query.filter_by(
            user_id=user_id,
            circle_type=circle_type
        ).first()
        
        if not circle:
            return {'posts': [], 'pagination': {}}
        
        # Get circle members
        member_ids = [m.user_id for m in CircleMember.query.filter_by(circle_id=circle.id).all()]
        
        # Include self
        member_ids.append(user_id)
        
        # Get posts from circle members
        query = Post.query.filter(
            Post.user_id.in_(member_ids),
            Post.is_deleted == False,
            or_(
                Post.visibility == 'general',
                and_(
                    Post.visibility == circle_type,
                    Post.circle_id == circle.id
                )
            )
        ).order_by(desc(Post.created_at))
        
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Format posts
        posts = []
        for post in paginated.items:
            author = User.query.get(post.user_id)
            
            posts.append({
                'id': post.id,
                'author': {
                    'id': author.anonymous_id,
                    'display_name': author.display_name
                },
                'content': decrypt_field(post.content_encrypted),
                'visibility': post.visibility,
                'created_at': post.created_at.isoformat(),
                'is_own': post.user_id == user_id
            })
        
        return {
            'posts': posts,
            'pagination': {
                'page': paginated.page,
                'pages': paginated.pages,
                'total': paginated.total
            }
        }
    
    def block_user(self, blocker_id, blocked_id):
        """Block a user"""
        # Store block in Redis for quick lookup
        block_key = f"blocked:{blocker_id}:{blocked_id}"
        self.redis.set(block_key, 1)
        
        # Also unfollow if following
        self.unfollow_user(blocker_id, blocked_id)
        self.unfollow_user(blocked_id, blocker_id)
        
        return True
    
    def unblock_user(self, blocker_id, blocked_id):
        """Unblock a user"""
        block_key = f"blocked:{blocker_id}:{blocked_id}"
        self.redis.delete(block_key)
        
        return True
    
    def is_blocked(self, user1_id, user2_id):
        """Check if either user has blocked the other"""
        block1 = f"blocked:{user1_id}:{user2_id}"
        block2 = f"blocked:{user2_id}:{user1_id}"
        
        return self.redis.exists(block1) or self.redis.exists(block2)
    
    def get_blocked_users(self, user_id):
        """Get list of blocked users"""
        from models import User
        
        # Find all block keys for this user
        pattern = f"blocked:{user_id}:*"
        blocked_keys = self.redis.keys(pattern)
        
        blocked_users = []
        for key in blocked_keys:
            # Extract blocked user ID from key
            blocked_id = int(key.decode().split(':')[-1])
            user = User.query.get(blocked_id)
            if user:
                blocked_users.append({
                    'id': user.anonymous_id,
                    'display_name': user.display_name
                })
        
        return blocked_users
