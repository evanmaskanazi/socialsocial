"""
Tracking and analytics module for Thera Social
Handles parameter tracking, trend analysis, and alerts
"""
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import numpy as np
from security import encrypt_field, decrypt_field
import re

class TrackingManager:
    """Manages parameter tracking and trend analysis"""
    
    def __init__(self, db, redis_client):
        self.db = db
        self.redis = redis_client
        
    def get_user_parameters(self, user_id):
        """Get all tracking parameters for user"""
        from models import Parameter, ParameterValue
        
        parameters = Parameter.query.filter_by(
            user_id=user_id,
            is_active=True
        ).all()
        
        result = []
        for param in parameters:
            # Get latest value
            latest_value = ParameterValue.query.filter_by(
                parameter_id=param.id
            ).order_by(desc(ParameterValue.recorded_at)).first()
            
            result.append({
                'id': param.id,
                'name': param.name,
                'type': param.parameter_type,
                'min_value': param.min_value,
                'max_value': param.max_value,
                'unit': param.unit,
                'latest_value': latest_value.value if latest_value else None,
                'latest_recorded': latest_value.recorded_at.isoformat() if latest_value else None
            })
        
        return result
    
    def record_value(self, user_id, parameter_id, value, notes=None):
        """Record a parameter value"""
        from models import Parameter, ParameterValue
        
        # Verify parameter belongs to user
        param = Parameter.query.filter_by(
            id=parameter_id,
            user_id=user_id
        ).first()
        
        if not param:
            raise ValueError("Parameter not found")
        
        # Validate value range
        if param.parameter_type == 'scale':
            if param.min_value is not None and value < param.min_value:
                raise ValueError(f"Value below minimum ({param.min_value})")
            if param.max_value is not None and value > param.max_value:
                raise ValueError(f"Value above maximum ({param.max_value})")
        
        # Create value record
        param_value = ParameterValue(
            parameter_id=parameter_id,
            user_id=user_id,
            value=float(value),
            notes_encrypted=encrypt_field(notes) if notes else None
        )
        
        self.db.session.add(param_value)
        
        try:
            self.db.session.commit()
            
            # Clear cache
            cache_key = f"param_history:{parameter_id}"
            self.redis.delete(cache_key)
            
            # Check for concerning patterns
            self._check_concerning_trends(user_id, parameter_id, value)
            
            return {
                'id': param_value.id,
                'value': param_value.value,
                'recorded_at': param_value.recorded_at.isoformat()
            }
            
        except Exception as e:
            self.db.session.rollback()
            raise e
    
    def get_parameter_history(self, user_id, parameter_id, days=30):
        """Get parameter history with statistics"""
        from models import Parameter, ParameterValue
        
        # Verify parameter belongs to user
        param = Parameter.query.filter_by(
            id=parameter_id,
            user_id=user_id
        ).first()
        
        if not param:
            return {'values': [], 'stats': {}}
        
        # Get values for period
        since = datetime.utcnow() - timedelta(days=days)
        
        values = ParameterValue.query.filter(
            ParameterValue.parameter_id == parameter_id,
            ParameterValue.recorded_at >= since
        ).order_by(desc(ParameterValue.recorded_at)).all()
        
        # Format values
        value_list = []
        raw_values = []
        
        for val in values:
            value_list.append({
                'id': val.id,
                'value': val.value,
                'notes': decrypt_field(val.notes_encrypted) if val.notes_encrypted else None,
                'recorded_at': val.recorded_at.isoformat()
            })
            raw_values.append(val.value)
        
        # Calculate statistics
        stats = {}
        if raw_values:
            stats = {
                'mean': float(np.mean(raw_values)),
                'median': float(np.median(raw_values)),
                'std_dev': float(np.std(raw_values)),
                'min': float(np.min(raw_values)),
                'max': float(np.max(raw_values)),
                'count': len(raw_values),
                'trend': self._calculate_trend(raw_values)
            }
        
        return {
            'values': value_list,
            'stats': stats
        }
    
    def analyze_trends(self, user_id, parameter_id):
        """Analyze trends for a parameter"""
        from models import Parameter, ParameterValue, Trend
        
        # Get recent values
        values = ParameterValue.query.filter_by(
            parameter_id=parameter_id,
            user_id=user_id
        ).order_by(ParameterValue.recorded_at).limit(30).all()
        
        if len(values) < 3:
            return None
        
        # Extract values and timestamps
        data_points = [(v.recorded_at.timestamp(), v.value) for v in values]
        values_only = [v.value for v in values]
        
        # Calculate trend
        trend_type = self._calculate_trend(values_only)
        
        # Calculate change percentage
        if len(values_only) >= 2:
            change_percent = ((values_only[-1] - values_only[0]) / values_only[0]) * 100
        else:
            change_percent = 0
        
        # Calculate confidence (based on consistency)
        confidence = self._calculate_confidence(values_only)
        
        # Store trend
        trend = Trend(
            user_id=user_id,
            parameter_id=parameter_id,
            trend_type=trend_type,
            confidence=confidence,
            change_percent=change_percent,
            period_days=len(values)
        )
        
        self.db.session.add(trend)
        
        try:
            self.db.session.commit()
        except Exception:
            self.db.session.rollback()
        
        return {
            'trend_type': trend_type,
            'confidence': confidence,
            'change_percent': change_percent,
            'period_days': len(values)
        }
    
    def create_alert(self, user_id, alert_type, message, priority='low'):
        """Create an alert for user"""
        from models import Alert
        
        alert = Alert(
            user_id=user_id,
            alert_type=alert_type,
            title=self._get_alert_title(alert_type),
            message_encrypted=encrypt_field(message),
            priority=priority
        )
        
        self.db.session.add(alert)
        
        try:
            self.db.session.commit()
            
            # Send real-time notification if high priority
            if priority in ['high', 'critical']:
                self._send_realtime_alert(user_id, alert.id)
            
            return alert.id
            
        except Exception:
            self.db.session.rollback()
            return None
    
    def get_user_alerts(self, user_id, page=1, per_page=20):
        """Get user's alerts"""
        from models import Alert
        
        # Get unread count
        unread_count = Alert.query.filter_by(
            user_id=user_id,
            is_read=False
        ).count()
        
        # Get paginated alerts
        query = Alert.query.filter_by(user_id=user_id)
        query = query.order_by(desc(Alert.created_at))
        
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        alerts = []
        for alert in paginated.items:
            alerts.append({
                'id': alert.id,
                'type': alert.alert_type,
                'title': alert.title,
                'message': decrypt_field(alert.message_encrypted),
                'priority': alert.priority,
                'is_read': alert.is_read,
                'created_at': alert.created_at.isoformat()
            })
        
        return {
            'alerts': alerts,
            'unread_count': unread_count,
            'pagination': {
                'page': paginated.page,
                'pages': paginated.pages,
                'total': paginated.total
            }
        }
    
    def mark_alert_read(self, user_id, alert_id):
        """Mark alert as read"""
        from models import Alert
        
        alert = Alert.query.filter_by(
            id=alert_id,
            user_id=user_id
        ).first()
        
        if alert:
            alert.is_read = True
            self.db.session.commit()
            return True
        
        return False
    
    def analyze_content(self, user_id, content):
        """Analyze content for concerning patterns"""
        concerning_keywords = {
            'suicide': 'critical',
            'self-harm': 'critical',
            'kill myself': 'critical',
            'end it all': 'critical',
            'depressed': 'high',
            'anxious': 'medium',
            'panic': 'high',
            'hopeless': 'high',
            'worthless': 'high',
            'cant sleep': 'medium',
            'insomnia': 'medium'
        }
        
        content_lower = content.lower()
        detected_concerns = []
        highest_priority = 'low'
        
        for keyword, priority in concerning_keywords.items():
            if keyword in content_lower:
                detected_concerns.append(keyword)
                
                # Update highest priority
                priority_levels = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
                if priority_levels.get(priority, 0) > priority_levels.get(highest_priority, 0):
                    highest_priority = priority
        
        if detected_concerns:
            # Create self-alert
            message = f"We noticed you mentioned: {', '.join(detected_concerns)}. "
            
            if highest_priority == 'critical':
                message += "Please reach out for support if you're in crisis. You can call 988 for immediate help."
            elif highest_priority == 'high':
                message += "Consider reaching out to your support network or a mental health professional."
            else:
                message += "Remember to take care of yourself. Your tracking data can help identify patterns."
            
            self.create_alert(
                user_id,
                'self_care_reminder',
                message,
                highest_priority
            )
            
            # Alert trusted contacts if critical
            if highest_priority == 'critical':
                self._alert_emergency_contacts(user_id, detected_concerns)
    
    def get_insights(self, user_id, days=30):
        """Generate insights from user's tracking data"""
        from models import Parameter, ParameterValue
        
        insights = []
        
        # Get all parameters
        parameters = Parameter.query.filter_by(
            user_id=user_id,
            is_active=True
        ).all()
        
        for param in parameters:
            # Get values for period
            since = datetime.utcnow() - timedelta(days=days)
            values = ParameterValue.query.filter(
                ParameterValue.parameter_id == param.id,
                ParameterValue.recorded_at >= since
            ).order_by(ParameterValue.recorded_at).all()
            
            if len(values) < 3:
                continue
            
            value_list = [v.value for v in values]
            
            # Analyze patterns
            trend = self._calculate_trend(value_list)
            avg = np.mean(value_list)
            std = np.std(value_list)
            
            # Generate insights
            if param.name.lower() in ['mood', 'energy', 'sleep']:
                if trend == 'decreasing' and avg < 5:
                    insights.append({
                        'type': 'concern',
                        'parameter': param.name,
                        'message': f"Your {param.name} has been declining and is below average"
                    })
                elif trend == 'increasing' and avg > 7:
                    insights.append({
                        'type': 'positive',
                        'parameter': param.name,
                        'message': f"Great job! Your {param.name} is improving"
                    })
            
            # Check volatility
            if std > 2:
                insights.append({
                    'type': 'observation',
                    'parameter': param.name,
                    'message': f"Your {param.name} has been fluctuating significantly"
                })
        
        # Check correlations
        correlations = self._find_correlations(user_id, days)
        for corr in correlations:
            insights.append({
                'type': 'correlation',
                'message': corr
            })
        
        return insights
    
    def _calculate_trend(self, values):
        """Calculate trend from values"""
        if len(values) < 2:
            return 'stable'
        
        # Simple linear regression
        x = list(range(len(values)))
        
        # Calculate slope
        n = len(values)
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(i**2 for i in x)
        
        if n * sum_x2 - sum_x**2 == 0:
            return 'stable'
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
        
        # Determine trend
        avg = np.mean(values)
        threshold = 0.1 * avg  # 10% of average
        
        if slope > threshold:
            return 'increasing'
        elif slope < -threshold:
            return 'decreasing'
        else:
            # Check for volatility
            std = np.std(values)
            if std > 0.3 * avg:
                return 'volatile'
            return 'stable'
    
    def _calculate_confidence(self, values):
        """Calculate confidence in trend"""
        if len(values) < 3:
            return 0.0
        
        # Calculate R-squared for linear fit
        x = list(range(len(values)))
        
        # Calculate means
        x_mean = np.mean(x)
        y_mean = np.mean(values)
        
        # Calculate R-squared
        ss_tot = sum((y - y_mean)**2 for y in values)
        
        if ss_tot == 0:
            return 0.0
        
        # Simple linear regression prediction
        n = len(values)
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(i**2 for i in x)
        
        if n * sum_x2 - sum_x**2 == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
        intercept = (sum_y - slope * sum_x) / n
        
        # Calculate predictions
        predictions = [slope * xi + intercept for xi in x]
        ss_res = sum((values[i] - predictions[i])**2 for i in range(n))
        
        r_squared = 1 - (ss_res / ss_tot)
        
        # Convert to confidence (0-100)
        return max(0, min(100, r_squared * 100))
    
    def _check_concerning_trends(self, user_id, parameter_id, new_value):
        """Check for concerning trends in parameters"""
        from models import Parameter, ParameterValue
        
        param = Parameter.query.get(parameter_id)
        if not param:
            return
        
        # Only check mood-related parameters
        if param.name.lower() not in ['mood', 'energy', 'anxiety', 'depression']:
            return
        
        # Get recent values
        recent_values = ParameterValue.query.filter_by(
            parameter_id=parameter_id,
            user_id=user_id
        ).order_by(desc(ParameterValue.recorded_at)).limit(7).all()
        
        if len(recent_values) < 3:
            return
        
        values = [v.value for v in recent_values]
        values.append(new_value)
        
        # Check for concerning patterns
        avg = np.mean(values)
        
        if param.name.lower() in ['mood', 'energy']:
            if avg < 3 and new_value < 3:
                self.create_alert(
                    user_id,
                    'low_mood_alert',
                    f"Your {param.name} has been consistently low. Consider reaching out to your support network.",
                    'high'
                )
        
        elif param.name.lower() in ['anxiety', 'depression']:
            if avg > 7 and new_value > 7:
                self.create_alert(
                    user_id,
                    'high_distress_alert',
                    f"Your {param.name} levels have been elevated. Remember to use your coping strategies.",
                    'high'
                )
    
    def _alert_emergency_contacts(self, user_id, concerns):
        """Alert emergency contacts for critical situations"""
        from models import Circle, CircleMember, Alert, User
        
        # Get family circle
        family_circle = Circle.query.filter_by(
            user_id=user_id,
            circle_type='family'
        ).first()
        
        if not family_circle:
            return
        
        # Get family members
        members = CircleMember.query.filter_by(circle_id=family_circle.id).all()
        
        user = User.query.get(user_id)
        
        for member in members:
            self.create_alert(
                member.user_id,
                'emergency_contact_alert',
                f"{user.display_name} may need immediate support. Detected concerns: {', '.join(concerns)}",
                'critical'
            )
    
    def _find_correlations(self, user_id, days=30):
        """Find correlations between parameters"""
        from models import Parameter, ParameterValue
        
        correlations = []
        
        # Get all parameters
        parameters = Parameter.query.filter_by(
            user_id=user_id,
            is_active=True
        ).all()
        
        if len(parameters) < 2:
            return correlations
        
        # Get values for each parameter
        param_values = {}
        since = datetime.utcnow() - timedelta(days=days)
        
        for param in parameters:
            values = ParameterValue.query.filter(
                ParameterValue.parameter_id == param.id,
                ParameterValue.recorded_at >= since
            ).order_by(ParameterValue.recorded_at).all()
            
            if values:
                param_values[param.name] = [v.value for v in values]
        
        # Find correlations
        for p1 in param_values:
            for p2 in param_values:
                if p1 >= p2:  # Avoid duplicates
                    continue
                
                if len(param_values[p1]) == len(param_values[p2]) and len(param_values[p1]) > 3:
                    correlation = np.corrcoef(param_values[p1], param_values[p2])[0, 1]
                    
                    if abs(correlation) > 0.7:
                        if correlation > 0:
                            correlations.append(f"{p1} and {p2} tend to move together")
                        else:
                            correlations.append(f"When {p1} increases, {p2} tends to decrease")
        
        return correlations[:3]  # Return top 3 correlations
    
    def _get_alert_title(self, alert_type):
        """Get title for alert type"""
        titles = {
            'new_follower': 'New Follower',
            'follower_trend_change': 'Follower Update',
            'self_care_reminder': 'Self-Care Reminder',
            'low_mood_alert': 'Mood Check-In',
            'high_distress_alert': 'Wellness Check',
            'emergency_contact_alert': 'Urgent: Support Needed',
            'trend_detected': 'Trend Detected',
            'milestone': 'Milestone Reached'
        }
        
        return titles.get(alert_type, 'Notification')
    
    def _send_realtime_alert(self, user_id, alert_id):
        """Send real-time alert through Redis pub/sub"""
        channel = f"alerts:{user_id}"
        message = {
            'alert_id': alert_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.redis.publish(channel, str(message))
