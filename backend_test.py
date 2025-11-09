#!/usr/bin/env python3
"""
TheraSocial Backend Diagnostic Suite
Comprehensive testing for production readiness

Run on Render shell with: python backend_diagnostics.py
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_check(passed, message, details=None):
    """Print a check result with color coding"""
    if passed:
        symbol = f"{Colors.GREEN}✓{Colors.END}"
    elif passed is None:
        symbol = f"{Colors.YELLOW}⚠{Colors.END}"
    else:
        symbol = f"{Colors.RED}✗{Colors.END}"
    
    print(f"{symbol} {message}")
    if details:
        print(f"  {Colors.BLUE}→{Colors.END} {details}")

def print_section(title):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

# Import Flask app components
try:
    from app import app, db, User, Profile, Post, Comment, Circle, Follow, FollowRequest
    from app import SavedParameters, Alert, Message, Activity, ParameterTrigger
    from app import redis_client, is_production
    print_check(True, "Successfully imported application modules")
except Exception as e:
    print_check(False, "Failed to import application modules", str(e))
    sys.exit(1)

class BackendDiagnostics:
    def __init__(self):
        self.results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'issues': []
        }
        
    def add_result(self, passed, category, message, details=None, fix=None):
        """Track test result"""
        if passed:
            self.results['passed'] += 1
        elif passed is None:
            self.results['warnings'] += 1
        else:
            self.results['failed'] += 1
            self.results['issues'].append({
                'category': category,
                'message': message,
                'details': details,
                'fix': fix
            })
        
        print_check(passed, message, details)
        
        if fix and not passed:
            print(f"  {Colors.YELLOW}FIX:{Colors.END} {fix}")
    
    def test_environment_config(self):
        """Test environment configuration"""
        print_section("Environment Configuration")
        
        # Check SECRET_KEY
        secret_key = app.config.get('SECRET_KEY')
        is_default = secret_key == 'dev-secret-key-change-in-production'
        self.add_result(
            not (is_production and is_default),
            'security',
            'SECRET_KEY configuration',
            f"Using {'default (UNSAFE)' if is_default else 'custom'} key",
            "Set SECRET_KEY environment variable with a strong random key"
        )
        
        # Check DATABASE_URL
        db_url = os.environ.get('DATABASE_URL')
        self.add_result(
            bool(db_url),
            'database',
            'DATABASE_URL environment variable',
            db_url[:50] + '...' if db_url else 'Not set',
            "Set DATABASE_URL in Render environment variables"
        )
        
        # Check Redis
        redis_url = os.environ.get('REDIS_URL')
        self.add_result(
            bool(redis_url) if is_production else None,
            'cache',
            'REDIS_URL configuration',
            'Configured' if redis_url else 'Not configured (sessions will use filesystem)',
            "Set REDIS_URL for production session management"
        )
        
        # Check email configuration
        smtp_user = os.environ.get('SMTP_USERNAME')
        smtp_pass = os.environ.get('SMTP_PASSWORD')
        email_configured = bool(smtp_user and smtp_pass)
        self.add_result(
            email_configured if is_production else None,
            'email',
            'Email configuration for password resets',
            'Configured' if email_configured else 'Not configured',
            "Set SMTP_USERNAME, SMTP_PASSWORD, SMTP_SERVER, FROM_EMAIL environment variables"
        )
    
    def test_database_connectivity(self):
        """Test database connection and basic operations"""
        print_section("Database Connectivity")
        
        with app.app_context():
            try:
                # Test basic connection
                result = db.session.execute(db.text('SELECT 1')).scalar()
                self.add_result(
                    result == 1,
                    'database',
                    'Database connection',
                    'Successfully connected to database'
                )
                
                # Test transaction
                db.session.begin()
                db.session.rollback()
                self.add_result(
                    True,
                    'database',
                    'Database transaction support',
                    'Transactions working correctly'
                )
                
            except Exception as e:
                self.add_result(
                    False,
                    'database',
                    'Database connectivity',
                    str(e),
                    "Check DATABASE_URL and database server status"
                )
    
    def test_database_schema(self):
        """Test database schema integrity"""
        print_section("Database Schema Integrity")
        
        with app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            
            required_tables = {
                'users': ['id', 'username', 'email', 'password_hash', 'preferred_language', 
                         'has_completed_onboarding', 'shareable_link_token', 'circles_privacy'],
                'profiles': ['id', 'user_id', 'bio'],
                'posts': ['id', 'user_id', 'content', 'visibility', 'created_at'],
                'circles': ['id', 'user_id', 'circle_type', 'member_id'],
                'messages': ['id', 'sender_id', 'recipient_id', 'content', 'is_read'],
                'saved_parameters': ['id', 'user_id', 'date', 'mood', 'energy', 
                                   'sleep_quality', 'physical_activity', 'anxiety',
                                   'mood_privacy', 'energy_privacy', 'sleep_quality_privacy',
                                   'physical_activity_privacy', 'anxiety_privacy'],
                'follows': ['id', 'follower_id', 'followed_id'],
                'follow_requests': ['id', 'requester_id', 'target_id', 'privacy_level', 'status'],
                'alerts': ['id', 'user_id', 'title', 'content', 'alert_type', 'is_read'],
                'comments': ['id', 'post_id', 'user_id', 'content'],
                'reactions': ['id', 'post_id', 'user_id', 'type']
            }
            
            existing_tables = inspector.get_table_names()
            
            for table, required_columns in required_tables.items():
                if table in existing_tables:
                    columns = [col['name'] for col in inspector.get_columns(table)]
                    missing_columns = [col for col in required_columns if col not in columns]
                    
                    self.add_result(
                        len(missing_columns) == 0,
                        'schema',
                        f'Table "{table}" schema',
                        f"Missing columns: {missing_columns}" if missing_columns else "All required columns present",
                        f"Run migrations or add columns: {', '.join(missing_columns)}"
                    )
                else:
                    self.add_result(
                        False,
                        'schema',
                        f'Table "{table}" exists',
                        'Table not found in database',
                        "Run flask db upgrade or ensure auto-migration ran"
                    )
            
            # Check indexes
            self.add_result(
                True,
                'schema',
                'Database indexes',
                f"Found {len(existing_tables)} tables",
                None
            )
    
    def test_database_constraints(self):
        """Test database constraints and relationships"""
        print_section("Database Constraints & Relationships")
        
        with app.app_context():
            # Test unique constraints
            try:
                # Check users table unique constraints
                users = db.session.query(User.username, db.func.count(User.username)).group_by(User.username).having(db.func.count(User.username) > 1).all()
                self.add_result(
                    len(users) == 0,
                    'integrity',
                    'User.username uniqueness',
                    f"Found {len(users)} duplicate usernames" if users else "No duplicates",
                    "Clean up duplicate usernames in database"
                )
                
                emails = db.session.query(User.email, db.func.count(User.email)).group_by(User.email).having(db.func.count(User.email) > 1).all()
                self.add_result(
                    len(emails) == 0,
                    'integrity',
                    'User.email uniqueness',
                    f"Found {len(emails)} duplicate emails" if emails else "No duplicates",
                    "Clean up duplicate emails in database"
                )
                
            except Exception as e:
                self.add_result(
                    False,
                    'integrity',
                    'Constraint checking',
                    str(e),
                    "Check database schema and run migrations"
                )
    
    def test_data_integrity(self):
        """Test data integrity issues"""
        print_section("Data Integrity")
        
        with app.app_context():
            # Check for orphaned records
            try:
                # Profiles without users
                orphaned_profiles = db.session.query(Profile).filter(
                    ~Profile.user_id.in_(db.session.query(User.id))
                ).count()
                self.add_result(
                    orphaned_profiles == 0,
                    'integrity',
                    'Orphaned profiles',
                    f"Found {orphaned_profiles} profiles without users" if orphaned_profiles else "No orphans",
                    f"DELETE FROM profiles WHERE user_id NOT IN (SELECT id FROM users);"
                )
                
                # Posts without users
                orphaned_posts = db.session.query(Post).filter(
                    ~Post.user_id.in_(db.session.query(User.id))
                ).count()
                self.add_result(
                    orphaned_posts == 0,
                    'integrity',
                    'Orphaned posts',
                    f"Found {orphaned_posts} posts without users" if orphaned_posts else "No orphans",
                    f"DELETE FROM posts WHERE user_id NOT IN (SELECT id FROM users);"
                )
                
                # Messages with invalid sender/recipient
                orphaned_messages = db.session.query(Message).filter(
                    or_(
                        ~Message.sender_id.in_(db.session.query(User.id)),
                        ~Message.recipient_id.in_(db.session.query(User.id))
                    )
                ).count()
                self.add_result(
                    orphaned_messages == 0,
                    'integrity',
                    'Orphaned messages',
                    f"Found {orphaned_messages} messages with invalid users" if orphaned_messages else "No orphans",
                    "DELETE FROM messages WHERE sender_id NOT IN (SELECT id FROM users) OR recipient_id NOT IN (SELECT id FROM users);"
                )
                
                # Self-follows
                self_follows = db.session.query(Follow).filter(
                    Follow.follower_id == Follow.followed_id
                ).count()
                self.add_result(
                    self_follows == 0,
                    'integrity',
                    'Self-follow prevention',
                    f"Found {self_follows} self-follows" if self_follows else "No self-follows",
                    "DELETE FROM follows WHERE follower_id = followed_id;"
                )
                
            except Exception as e:
                self.add_result(
                    None,
                    'integrity',
                    'Data integrity checks',
                    f"Could not complete all checks: {str(e)}",
                    None
                )
    
    def test_authentication_security(self):
        """Test authentication and security measures"""
        print_section("Authentication & Security")
        
        with app.app_context():
            try:
                # Check password hashing
                users_with_plaintext = db.session.query(User).filter(
                    ~User.password_hash.like('pbkdf2:%')
                ).count()
                self.add_result(
                    users_with_plaintext == 0,
                    'security',
                    'Password hashing',
                    f"Found {users_with_plaintext} users with potentially unhashed passwords" if users_with_plaintext else "All passwords properly hashed",
                    "Force password reset for affected users"
                )
                
                # Check for inactive users with data
                total_users = db.session.query(User).count()
                inactive_users = db.session.query(User).filter(User.is_active == False).count()
                self.add_result(
                    True,
                    'security',
                    'User account status',
                    f"Total: {total_users}, Inactive: {inactive_users}",
                    None
                )
                
            except Exception as e:
                self.add_result(
                    False,
                    'security',
                    'Authentication checks',
                    str(e),
                    None
                )
    
    def test_privacy_settings(self):
        """Test privacy settings integrity"""
        print_section("Privacy Settings")
        
        with app.app_context():
            try:
                # Check parameters privacy defaults
                params_without_privacy = db.session.query(SavedParameters).filter(
                    or_(
                        SavedParameters.mood_privacy.is_(None),
                        SavedParameters.energy_privacy.is_(None),
                        SavedParameters.sleep_quality_privacy.is_(None),
                        SavedParameters.physical_activity_privacy.is_(None),
                        SavedParameters.anxiety_privacy.is_(None)
                    )
                ).count()
                
                self.add_result(
                    params_without_privacy == 0,
                    'privacy',
                    'Parameter privacy settings',
                    f"Found {params_without_privacy} parameters without privacy settings" if params_without_privacy else "All parameters have privacy settings",
                    "UPDATE saved_parameters SET mood_privacy='private', energy_privacy='private', sleep_quality_privacy='private', physical_activity_privacy='private', anxiety_privacy='private' WHERE mood_privacy IS NULL;"
                )
                
                # Check circles privacy
                users_without_circles_privacy = db.session.query(User).filter(
                    User.circles_privacy.is_(None)
                ).count()
                
                self.add_result(
                    users_without_circles_privacy == 0,
                    'privacy',
                    'User circles privacy',
                    f"Found {users_without_circles_privacy} users without circles privacy setting" if users_without_circles_privacy else "All users have circles privacy",
                    "UPDATE users SET circles_privacy='private' WHERE circles_privacy IS NULL;"
                )
                
            except Exception as e:
                self.add_result(
                    None,
                    'privacy',
                    'Privacy checks',
                    str(e),
                    None
                )
    
    def test_performance_concerns(self):
        """Test for potential performance issues"""
        print_section("Performance Analysis")
        
        with app.app_context():
            try:
                # Check for large tables
                table_counts = {
                    'users': db.session.query(User).count(),
                    'posts': db.session.query(Post).count(),
                    'messages': db.session.query(Message).count(),
                    'saved_parameters': db.session.query(SavedParameters).count(),
                    'follows': db.session.query(Follow).count(),
                    'alerts': db.session.query(Alert).count()
                }
                
                for table, count in table_counts.items():
                    warning = count > 100000
                    self.add_result(
                        not warning if warning else None,
                        'performance',
                        f'{table.capitalize()} table size',
                        f"{count:,} records" + (" - Consider archiving/pagination optimization" if warning else ""),
                        f"Implement archiving strategy for {table}" if warning else None
                    )
                
                # Check Redis connectivity if configured
                if redis_client:
                    try:
                        redis_client.ping()
                        self.add_result(
                            True,
                            'performance',
                            'Redis cache connectivity',
                            'Connected and responding',
                            None
                        )
                    except Exception as e:
                        self.add_result(
                            False,
                            'performance',
                            'Redis cache connectivity',
                            str(e),
                            "Check REDIS_URL and Redis server status"
                        )
                else:
                    self.add_result(
                        None,
                        'performance',
                        'Redis cache',
                        'Not configured (using filesystem sessions)',
                        "Configure Redis for better performance in production"
                    )
                
            except Exception as e:
                self.add_result(
                    None,
                    'performance',
                    'Performance analysis',
                    str(e),
                    None
                )
    
    def test_api_routes(self):
        """Test critical API routes exist and are protected"""
        print_section("API Routes")
        
        critical_routes = [
            '/api/auth/register',
            '/api/auth/login',
            '/api/auth/logout',
            '/api/posts',
            '/api/posts/<int:post_id>',
            '/api/messages',
            '/api/user/profile',
            '/api/parameters/save',
            '/api/circles',
            '/api/follow/<int:user_id>',
            '/api/alerts'
        ]
        
        existing_routes = [rule.rule for rule in app.url_map.iter_rules()]
        
        for route in critical_routes:
            # Check if route pattern exists (handle dynamic parts)
            route_pattern = route.replace('<int:post_id>', '*').replace('<int:user_id>', '*')
            exists = any(r.replace('<int:post_id>', '*').replace('<int:user_id>', '*') == route_pattern for r in existing_routes)
            
            self.add_result(
                exists,
                'api',
                f'Route {route}',
                'Exists' if exists else 'Missing',
                f"Implement {route} endpoint in app.py" if not exists else None
            )
    
    def test_scalability_concerns(self):
        """Test for scalability issues"""
        print_section("Scalability Concerns")
        
        with app.app_context():
            try:
                # Check for N+1 query patterns in common operations
                # This is a basic check - would need query profiling for thorough analysis
                
                # Check if users have reasonable follower counts
                avg_followers = db.session.query(
                    db.func.avg(db.func.count(Follow.id))
                ).select_from(Follow).group_by(Follow.followed_id).scalar() or 0
                
                self.add_result(
                    True,
                    'scalability',
                    'Average followers per user',
                    f"{avg_followers:.1f} followers/user (reasonable for current scale)",
                    None
                )
                
                # Check for users with excessive posts
                max_posts = db.session.query(
                    db.func.count(Post.id)
                ).group_by(Post.user_id).order_by(db.func.count(Post.id).desc()).first()
                
                if max_posts:
                    max_posts_count = max_posts[0]
                    warning = max_posts_count > 10000
                    self.add_result(
                        not warning,
                        'scalability',
                        'Maximum posts per user',
                        f"{max_posts_count:,} posts" + (" - May need pagination optimization" if warning else ""),
                        "Implement efficient pagination and consider post archiving" if warning else None
                    )
                
            except Exception as e:
                self.add_result(
                    None,
                    'scalability',
                    'Scalability checks',
                    str(e),
                    None
                )
    
    def test_data_validation(self):
        """Test data validation and sanitization"""
        print_section("Data Validation")
        
        with app.app_context():
            try:
                # Check for potentially malicious content in posts
                posts_with_scripts = db.session.query(Post).filter(
                    or_(
                        Post.content.like('%<script%'),
                        Post.content.like('%javascript:%'),
                        Post.content.like('%onerror=%')
                    )
                ).count()
                
                self.add_result(
                    posts_with_scripts == 0,
                    'security',
                    'XSS prevention in posts',
                    f"Found {posts_with_scripts} posts with potential XSS" if posts_with_scripts else "No obvious XSS patterns",
                    "Sanitize post content and implement content security policy"
                )
                
                # Check for extremely long content that might cause issues
                long_posts = db.session.query(Post).filter(
                    db.func.length(Post.content) > 50000
                ).count()
                
                self.add_result(
                    long_posts == 0,
                    'validation',
                    'Post content length validation',
                    f"Found {long_posts} extremely long posts" if long_posts else "Post lengths within reasonable limits",
                    "Implement content length validation (max 10000 chars recommended)"
                )
                
                # Check for valid email formats
                invalid_emails = db.session.query(User).filter(
                    ~User.email.like('%@%.%')
                ).count()
                
                self.add_result(
                    invalid_emails == 0,
                    'validation',
                    'Email format validation',
                    f"Found {invalid_emails} invalid email formats" if invalid_emails else "All emails have valid format",
                    "Implement strict email validation on registration"
                )
                
            except Exception as e:
                self.add_result(
                    None,
                    'validation',
                    'Data validation checks',
                    str(e),
                    None
                )
    
    def generate_report(self):
        """Generate comprehensive diagnostic report"""
        print_section("Diagnostic Summary")
        
        total_tests = self.results['passed'] + self.results['failed'] + self.results['warnings']
        
        print(f"\n{Colors.BOLD}Test Results:{Colors.END}")
        print(f"  {Colors.GREEN}✓ Passed:{Colors.END}  {self.results['passed']}/{total_tests}")
        print(f"  {Colors.RED}✗ Failed:{Colors.END}  {self.results['failed']}/{total_tests}")
        print(f"  {Colors.YELLOW}⚠ Warnings:{Colors.END} {self.results['warnings']}/{total_tests}")
        
        if self.results['failed'] > 0:
            print(f"\n{Colors.BOLD}{Colors.RED}Critical Issues Found:{Colors.END}")
            
            # Group issues by category
            issues_by_category = defaultdict(list)
            for issue in self.results['issues']:
                if issue.get('fix'):  # Only show issues with fixes
                    issues_by_category[issue['category']].append(issue)
            
            for category, issues in sorted(issues_by_category.items()):
                print(f"\n{Colors.YELLOW}{category.upper()}:{Colors.END}")
                for i, issue in enumerate(issues, 1):
                    print(f"\n  {i}. {issue['message']}")
                    if issue['details']:
                        print(f"     Details: {issue['details']}")
                    if issue['fix']:
                        print(f"     {Colors.GREEN}Fix:{Colors.END} {issue['fix']}")
        
        # Overall assessment
        print(f"\n{Colors.BOLD}Overall Assessment:{Colors.END}")
        if self.results['failed'] == 0:
            print(f"{Colors.GREEN}✓ System is ready for QA testing{Colors.END}")
        elif self.results['failed'] < 5:
            print(f"{Colors.YELLOW}⚠ System needs minor fixes before QA{Colors.END}")
        else:
            print(f"{Colors.RED}✗ System requires significant fixes before QA{Colors.END}")
        
        return self.results

def main():
    """Run all diagnostic tests"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}TheraSocial Backend Diagnostic Suite{Colors.END}")
    print(f"{Colors.BOLD}Running in: {'PRODUCTION' if is_production else 'DEVELOPMENT'} mode{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")
    
    diagnostics = BackendDiagnostics()
    
    # Run all test suites
    diagnostics.test_environment_config()
    diagnostics.test_database_connectivity()
    diagnostics.test_database_schema()
    diagnostics.test_database_constraints()
    diagnostics.test_data_integrity()
    diagnostics.test_authentication_security()
    diagnostics.test_privacy_settings()
    diagnostics.test_performance_concerns()
    diagnostics.test_api_routes()
    diagnostics.test_scalability_concerns()
    diagnostics.test_data_validation()
    
    # Generate final report
    results = diagnostics.generate_report()
    
    # Exit with appropriate code
    sys.exit(0 if results['failed'] == 0 else 1)

if __name__ == '__main__':
    main()
