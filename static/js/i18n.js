// Language detection and translation system with backend sync
const translations = {
    en: {
        // Navigation & Menu
        'nav.logo': 'TheraSocial',
        'nav.home': 'Home',
        'nav.about': 'About',
        'nav.support': 'Support',
        'nav.logout': 'Logout',
        'menu.feed': 'Feed',
        'menu.profile': 'Profile',
        'menu.circles': 'Circles',
        'menu.messages': 'Messages',
        'menu.parameters': 'Parameters',
        'menu.logout': 'Logout',
        
        // Authentication
        'auth.welcome': 'Welcome to TheraSocial',
        'auth.subtitle': 'Connect, share, and grow together',
        'auth.email': 'Email',
        'auth.email_placeholder': 'Enter your email',
        'auth.password': 'Password',
        'auth.password_placeholder': 'Enter your password',
        'auth.signin': 'Sign In',
        'auth.signup': 'Sign Up',
        'auth.toggle_signup': 'Don\'t have an account? Sign up',
        'auth.toggle_signin': 'Already have an account? Sign in',
        'auth.forgot_password': 'Forgot password?',
        'auth.remember_me': 'Remember me',
        'auth.or': 'OR',
        'auth.login_error': 'Invalid email or password',
        'auth.signup_success': 'Account created successfully!',
        'auth.name': 'Full Name',
        'auth.name_placeholder': 'Enter your full name',
        'auth.confirm_password': 'Confirm Password',
        'auth.confirm_password_placeholder': 'Re-enter your password',
        
        // Common buttons
        'btn.signin': 'Sign In',
        'btn.signup': 'Sign Up',
        'btn.save': 'Save',
        'btn.cancel': 'Cancel',
        'btn.submit': 'Submit',
        'btn.delete': 'Delete',
        'btn.edit': 'Edit',
        'btn.close': 'Close',
        'btn.send': 'Send',
        'btn.remove': 'Remove',
        'btn.add': 'Add',
        'btn.load': 'Load',
        'btn.clear': 'Clear',
        'btn.today': 'Today',
        'btn.logout': 'Logout',
        
        // Feed page
        'feed.title': 'My Feed',
        'feed.subtitle': 'Share your thoughts and connect with others',
        'feed.placeholder': 'What\'s on your mind?',
        'feed.calendar_title': 'Daily Activity Tracker',
        'feed.load_day': 'Load Day',
        'feed.save_day': 'Save Day',
        'feed.load_update': 'Load Update',
        'feed.save_update': 'Save Update',
        'feed.today': 'Today',
        'feed.selected_date': 'Selected Date',
        'feed.mood_notes': 'Daily Mood & Notes',
        'feed.how_feeling': 'How are you feeling today?',
        'feed.select_mood': 'Select mood...',
        'feed.daily_reflection': 'Daily reflection:',
        'feed.reflection_placeholder': 'How was your day? Any thoughts or feelings to record?',
        'feed.posts_today': 'Posts Today',
        'feed.messages_sent': 'Messages Sent',
        'feed.comments_made': 'Comments Made',
        'feed.activity_history': 'Your Activity History',
        'feed.loaded_activity': 'Loaded activity for',
        'feed.no_activity': 'No activity found for this date',
        'feed.activity_saved': 'Activity saved for',
        'feed.select_date': 'Please select a date',
        'feed.no_saved_activity': 'No saved activity yet. Start tracking today!',
        'feed.more_dates': 'more dates',
        
        // Calendar
        'calendar.prev': 'Previous',
        'calendar.next': 'Next',
        'calendar.today': 'Today',
        'calendar.days': 'Days',
        'calendar.month_year': '{month} {year}',
        
        // Visibility settings
        'visibility.general': 'General',
        'visibility.close_friends': 'Close Friends',
        'visibility.family': 'Family',
        'visibility.private': 'Private',
        
        // Alerts
        'alerts.title': 'Notifications',
        'alerts.no_alerts': 'No notifications yet',
        'alerts.mark_read': 'Mark as read',
        'alerts.clear_all': 'Clear all',
        
        // Circles page
        'circles.title': 'My Circles',
        'circles.subtitle': 'Organize your connections into meaningful groups',
        'circles.search_placeholder': 'Search users by name or email...',
        'circles.general': 'General',
        'circles.close_friends': 'Close Friends',
        'circles.family': 'Family',
        'circles.no_members': 'No members yet',
        'circles.add_to_circle': 'Add to Circle',
        'circles.no_users_found': 'No users found',
        'circles.user_added': 'added to',
        'circles.circle': 'circle!',
        'circles.remove_confirm': 'Remove this user from the circle?',
        'circles.user_removed': 'User removed from circle',
        
        // Messages page
        'messages.title': 'Messages',
        'messages.new': '+ New',
        'messages.select_conversation': 'Select a conversation',
        'messages.no_conversations': 'No conversations yet',
        'messages.type_message': 'Type a message...',
        'messages.send': 'Send',
        'messages.search': 'Search conversations',
        'messages.search_placeholder': 'Search messages...',
        'messages.no_messages': 'No messages yet',
        'messages.start_conversation': 'No messages yet. Start the conversation!',
        'messages.new_message': 'New Message',
        'messages.select_recipient': 'Select recipient...',
        'messages.select_and_type': 'Please select a recipient and enter a message',
        'messages.message_sent': 'Message sent!',
        
        // Moods
        'mood.great': '😊 Great',
        'mood.good': '🙂 Good',
        'mood.okay': '😐 Okay',
        'mood.down': '😔 Down',
        'mood.anxious': '😰 Anxious',
        'mood.tired': '😴 Tired',
        'mood.frustrated': '😡 Frustrated',
        'mood.hopeful': '🤗 Hopeful',
        'mood.happy': '😊 Happy',
        'mood.calm': '😌 Calm',
        'mood.sad': '😢 Sad',
        'mood.energetic': '🔥 Energetic',
        
        // Parameters page
        'parameters.title': 'Daily Parameters',
        'parameters.select_date': 'Select Date',
        'parameters.current_date': 'Current Date:',
        'parameters.insights': 'Insights',
        'parameters.mood': 'Mood',
        'parameters.mood_placeholder': 'How are you feeling? (e.g., Happy, Calm, Anxious, etc.)',
        'parameters.sleep': 'Sleep',
        'parameters.sleep_hours': 'Hours',
        'parameters.exercise': 'Exercise',
        'parameters.exercise_placeholder': 'What exercise did you do? (e.g., Running, Yoga, Gym, Walking)',
        'parameters.anxiety': 'Anxiety Level',
        'parameters.anxiety_placeholder': 'Describe your anxiety level (e.g., None, Mild, Moderate, Severe)',
        'parameters.energy': 'Energy Level',
        'parameters.energy_placeholder': 'Describe your energy level (e.g., Very Low, Low, Normal, High, Very High)',
        'parameters.notes': 'Notes',
        'parameters.notes_placeholder': 'Any additional notes or thoughts for today...',
        'parameters.save': 'Save Parameters',
        'parameters.load': 'Load Parameters',
        'parameters.clear': 'Clear',
        'parameters.saved': 'Parameters saved successfully',
        'parameters.loaded': 'Loaded parameters from',
        'parameters.no_saved': 'No saved parameters for this date',
        'parameters.cleared': 'Parameters cleared',
        'parameters.today_label': 'Today',
        
        // Profile page
        'profile.title': 'My Profile',
        'profile.loading': 'Loading...',
        'profile.completion': 'Profile Completion:',
        'profile.about_me': 'About Me',
        'profile.bio': 'Bio',
        'profile.bio_placeholder': 'Tell us about yourself...',
        'profile.professional': 'Professional',
        'profile.occupation': 'Occupation',
        'profile.occupation_placeholder': 'What do you do?',
        'profile.goals_aspirations': 'Goals & Aspirations',
        'profile.goals': 'My Goals',
        'profile.my_goals': 'My Goals',
        'profile.goals_placeholder': 'What are your personal or professional goals?',
        'profile.interests_hobbies': 'Interests & Hobbies',
        'profile.interests': 'Interests',
        'profile.interests_placeholder': 'What are you interested in?',
        'profile.hobbies': 'Favorite Hobbies',
        'profile.favorite_hobbies': 'Favorite Hobbies',
        'profile.hobbies_placeholder': 'What do you love to do in your free time?',
        'profile.save_changes': 'Save Changes',
        'profile.cancel': 'Cancel',
        'profile.updated': 'Profile updated successfully!',
        
        // Days of week
        'day.sun': 'Sun',
        'day.mon': 'Mon',
        'day.tue': 'Tue',
        'day.wed': 'Wed',
        'day.thu': 'Thu',
        'day.fri': 'Fri',
        'day.sat': 'Sat',
        
        // Months
        'month.january': 'January',
        'month.february': 'February',
        'month.march': 'March',
        'month.april': 'April',
        'month.may': 'May',
        'month.june': 'June',
        'month.july': 'July',
        'month.august': 'August',
        'month.september': 'September',
        'month.october': 'October',
        'month.november': 'November',
        'month.december': 'December',
        
        // Error messages
        'error.loading': 'Error loading data',
        'error.saving': 'Error saving data',
        'error.required': 'This field is required',
        'error.server': 'Server error. Please try again.',
        
        // Success messages
        'success.saved': 'Saved successfully',
        'success.updated': 'Updated successfully',
        'success.deleted': 'Deleted successfully'
    },
    
    he: {
        // Navigation & Menu
        'nav.logo': 'TheraSocial',
        'nav.home': 'בית',
        'nav.about': 'אודות',
        'nav.support': 'תמיכה',
        'menu.feed': 'פיד',
        'menu.profile': 'פרופיל',
        'menu.circles': 'מעגלים',
        'menu.messages': 'הודעות',
        'menu.parameters': 'פרמטרים',
        'menu.logout': 'התנתקות',
        
        // Authentication
        'auth.welcome': 'ברוכים הבאים ל-TheraSocial',
        'auth.subtitle': 'התחברו, שתפו וצמחו ביחד',
        'auth.email': 'אימייל',
        'auth.email_placeholder': 'הזן את האימייל שלך',
        'auth.password': 'סיסמה',
        'auth.password_placeholder': 'הזן את הסיסמה שלך',
        'auth.signin': 'התחברות',
        'auth.signup': 'הרשמה',
        'auth.toggle_signup': 'אין לך חשבון? הירשם',
        'auth.toggle_signin': 'כבר יש לך חשבון? התחבר',
        'auth.forgot_password': 'שכחת סיסמה?',
        'auth.remember_me': 'זכור אותי',
        'auth.or': 'או',
        'auth.login_error': 'אימייל או סיסמה שגויים',
        'auth.signup_success': 'החשבון נוצר בהצלחה!',
        'auth.name': 'שם מלא',
        'auth.name_placeholder': 'הזן את שמך המלא',
        'auth.confirm_password': 'אימות סיסמה',
        'auth.confirm_password_placeholder': 'הזן שוב את הסיסמה',
        
        // Common buttons
        'btn.signin': 'התחברות',
        'btn.signup': 'הרשמה',
        'btn.save': 'שמור',
        'btn.cancel': 'ביטול',
        'btn.submit': 'שלח',
        'btn.delete': 'מחק',
        'btn.edit': 'ערוך',
        'btn.close': 'סגור',
        'btn.send': 'שלח',
        'btn.remove': 'הסר',
        'btn.add': 'הוסף',
        'btn.load': 'טען',
        'btn.clear': 'נקה',
        'btn.today': 'היום',
        'btn.logout': 'התנתקות',
        
        // Feed page
        'feed.title': 'הפיד שלי',
        'feed.subtitle': 'שתף את המחשבות שלך והתחבר לאחרים',
        'feed.placeholder': 'מה עובר לך בראש?',
        'feed.calendar_title': 'מעקב פעילות יומית',
        'feed.load_day': 'טען יום',
        'feed.save_day': 'שמור יום',
        'feed.load_update': 'טען עדכון',
        'feed.save_update': 'שמור עדכון',
        'feed.today': 'היום',
        'feed.selected_date': 'תאריך נבחר',
        'feed.mood_notes': 'מצב רוח והערות יומיות',
        'feed.how_feeling': 'איך אתה מרגיש היום?',
        'feed.select_mood': 'בחר מצב רוח...',
        'feed.daily_reflection': 'הרהור יומי:',
        'feed.reflection_placeholder': 'איך היה היום שלך? מחשבות או רגשות לרשום?',
        'feed.posts_today': 'פוסטים היום',
        'feed.messages_sent': 'הודעות שנשלחו',
        'feed.comments_made': 'תגובות שנעשו',
        'feed.activity_history': 'היסטוריית הפעילות שלך',
        'feed.loaded_activity': 'נטענה פעילות עבור',
        'feed.no_activity': 'לא נמצאה פעילות לתאריך זה',
        'feed.activity_saved': 'הפעילות נשמרה עבור',
        'feed.select_date': 'אנא בחר תאריך',
        'feed.no_saved_activity': 'אין פעילות שמורה עדיין. התחל לעקוב היום!',
        'feed.more_dates': 'תאריכים נוספים',
        
        // Calendar
        'calendar.prev': 'קודם',
        'calendar.next': 'הבא',
        'calendar.today': 'היום',
        'calendar.days': 'ימים',
        'calendar.month_year': '{month} {year}',
        
        // Visibility settings
        'visibility.general': 'כללי',
        'visibility.close_friends': 'חברים קרובים',
        'visibility.family': 'משפחה',
        'visibility.private': 'פרטי',
        
        // Alerts
        'alerts.title': 'התראות',
        'alerts.no_alerts': 'אין התראות עדיין',
        'alerts.mark_read': 'סמן כנקרא',
        'alerts.clear_all': 'נקה הכל',
        
        // Circles page
        'circles.title': 'המעגלים שלי',
        'circles.subtitle': 'ארגן את הקשרים שלך לקבוצות משמעותיות',
        'circles.search_placeholder': 'חפש משתמשים לפי שם או אימייל...',
        'circles.general': 'כללי',
        'circles.close_friends': 'חברים קרובים',
        'circles.family': 'משפחה',
        'circles.no_members': 'אין חברים עדיין',
        'circles.add_to_circle': 'הוסף למעגל',
        'circles.no_users_found': 'לא נמצאו משתמשים',
        'circles.user_added': 'נוסף ל',
        'circles.circle': 'מעגל!',
        'circles.remove_confirm': 'להסיר משתמש זה מהמעגל?',
        'circles.user_removed': 'המשתמש הוסר מהמעגל',
        
        // Messages page
        'messages.title': 'הודעות',
        'messages.new': '+ חדש',
        'messages.select_conversation': 'בחר שיחה',
        'messages.no_conversations': 'אין שיחות עדיין',
        'messages.type_message': 'הקלד הודעה...',
        'messages.send': 'שלח',
        'messages.search': 'חפש שיחות',
        'messages.search_placeholder': 'חפש הודעות...',
        'messages.no_messages': 'אין הודעות עדיין',
        'messages.start_conversation': 'אין הודעות עדיין. התחל את השיחה!',
        'messages.new_message': 'הודעה חדשה',
        'messages.select_recipient': 'בחר נמען...',
        'messages.select_and_type': 'אנא בחר נמען והזן הודעה',
        'messages.message_sent': 'ההודעה נשלחה!',
        
        // Moods
        'mood.great': '😊 מצוין',
        'mood.good': '🙂 טוב',
        'mood.okay': '😐 בסדר',
        'mood.down': '😔 מדוכא',
        'mood.anxious': '😰 חרד',
        'mood.tired': '😴 עייף',
        'mood.frustrated': '😡 מתוסכל',
        'mood.hopeful': '🤗 מלא תקווה',
        'mood.happy': '😊 שמח',
        'mood.calm': '😌 רגוע',
        'mood.sad': '😢 עצוב',
        'mood.energetic': '🔥 אנרגטי',
        
        // Parameters page
        'parameters.title': 'פרמטרים יומיים',
        'parameters.select_date': 'בחר תאריך',
        'parameters.current_date': 'תאריך נוכחי:',
        'parameters.insights': 'תובנות',
        'parameters.mood': 'מצב רוח',
        'parameters.mood_placeholder': 'איך אתה מרגיש? (למשל, שמח, רגוע, חרד וכו\')',
        'parameters.sleep': 'שינה',
        'parameters.sleep_hours': 'שעות',
        'parameters.exercise': 'פעילות גופנית',
        'parameters.exercise_placeholder': 'איזו פעילות גופנית עשית? (למשל, ריצה, יוגה, חדר כושר, הליכה)',
        'parameters.anxiety': 'רמת חרדה',
        'parameters.anxiety_placeholder': 'תאר את רמת החרדה שלך (למשל, ללא, קלה, בינונית, חמורה)',
        'parameters.energy': 'רמת אנרגיה',
        'parameters.energy_placeholder': 'תאר את רמת האנרגיה שלך (למשל, נמוכה מאוד, נמוכה, רגילה, גבוהה, גבוהה מאוד)',
        'parameters.notes': 'הערות',
        'parameters.notes_placeholder': 'הערות או מחשבות נוספות להיום...',
        'parameters.save': 'שמור פרמטרים',
        'parameters.load': 'טען פרמטרים',
        'parameters.clear': 'נקה',
        'parameters.saved': 'הפרמטרים נשמרו בהצלחה',
        'parameters.loaded': 'נטענו פרמטרים מ',
        'parameters.no_saved': 'אין פרמטרים שמורים לתאריך זה',
        'parameters.cleared': 'הפרמטרים נוקו',
        'parameters.today_label': 'היום',
        
        // Profile page
        'profile.title': 'הפרופיל שלי',
        'profile.loading': 'טוען...',
        'profile.completion': 'השלמת פרופיל:',
        'profile.about_me': 'אודותיי',
        'profile.bio': 'ביוגרפיה',
        'profile.bio_placeholder': 'ספר לנו על עצמך...',
        'profile.professional': 'מקצועי',
        'profile.occupation': 'עיסוק',
        'profile.occupation_placeholder': 'מה אתה עושה?',
        'profile.goals_aspirations': 'מטרות ושאיפות',
        'profile.goals': 'המטרות שלי',
        'profile.my_goals': 'המטרות שלי',
        'profile.goals_placeholder': 'מהן המטרות האישיות או המקצועיות שלך?',
        'profile.interests_hobbies': 'תחומי עניין ותחביבים',
        'profile.interests': 'תחומי עניין',
        'profile.interests_placeholder': 'במה אתה מתעניין?',
        'profile.hobbies': 'תחביבים מועדפים',
        'profile.favorite_hobbies': 'תחביבים מועדפים',
        'profile.hobbies_placeholder': 'מה אתה אוהב לעשות בזמן הפנוי שלך?',
        'profile.save_changes': 'שמור שינויים',
        'profile.cancel': 'ביטול',
        'profile.updated': 'הפרופיל עודכן בהצלחה!',
        
        // Days of week
        'day.sun': 'א\'',
        'day.mon': 'ב\'',
        'day.tue': 'ג\'',
        'day.wed': 'ד\'',
        'day.thu': 'ה\'',
        'day.fri': 'ו\'',
        'day.sat': 'ש\'',
        
        // Months
        'month.january': 'ינואר',
        'month.february': 'פברואר',
        'month.march': 'מרץ',
        'month.april': 'אפריל',
        'month.may': 'מאי',
        'month.june': 'יוני',
        'month.july': 'יולי',
        'month.august': 'אוגוסט',
        'month.september': 'ספטמבר',
        'month.october': 'אוקטובר',
        'month.november': 'נובמבר',
        'month.december': 'דצמבר',
        
        // Error messages
        'error.loading': 'שגיאה בטעינת נתונים',
        'error.saving': 'שגיאה בשמירת נתונים',
        'error.required': 'שדה חובה',
        'error.server': 'שגיאת שרת. נסה שוב.',
        
        // Success messages
        'success.saved': 'נשמר בהצלחה',
        'success.updated': 'עודכן בהצלחה',
        'success.deleted': 'נמחק בהצלחה'
    },
    
    ar: {
        // Navigation & Menu
        'nav.logo': 'TheraSocial',
        'nav.home': 'الرئيسية',
        'nav.about': 'حول',
        'nav.support': 'الدعم',
        'menu.feed': 'التغذية',
        'menu.profile': 'الملف الشخصي',
        'menu.circles': 'الدوائر',
        'menu.messages': 'الرسائل',
        'menu.parameters': 'المعاملات',
        'menu.logout': 'تسجيل الخروج',
        
        // Authentication
        'auth.welcome': 'مرحبًا بك في TheraSocial',
        'auth.subtitle': 'تواصل، شارك، واكبر معًا',
        'auth.email': 'البريد الإلكتروني',
        'auth.email_placeholder': 'أدخل بريدك الإلكتروني',
        'auth.password': 'كلمة المرور',
        'auth.password_placeholder': 'أدخل كلمة المرور',
        'auth.signin': 'تسجيل الدخول',
        'auth.signup': 'إنشاء حساب',
        'auth.toggle_signup': 'ليس لديك حساب؟ سجل الآن',
        'auth.toggle_signin': 'لديك حساب بالفعل؟ سجل الدخول',
        'auth.forgot_password': 'نسيت كلمة المرور؟',
        'auth.remember_me': 'تذكرني',
        'auth.or': 'أو',
        'auth.login_error': 'البريد الإلكتروني أو كلمة المرور غير صحيحة',
        'auth.signup_success': 'تم إنشاء الحساب بنجاح!',
        'auth.name': 'الاسم الكامل',
        'auth.name_placeholder': 'أدخل اسمك الكامل',
        'auth.confirm_password': 'تأكيد كلمة المرور',
        'auth.confirm_password_placeholder': 'أعد إدخال كلمة المرور',
        
        // Common buttons
        'btn.signin': 'تسجيل الدخول',
        'btn.signup': 'إنشاء حساب',
        'btn.save': 'حفظ',
        'btn.cancel': 'إلغاء',
        'btn.submit': 'إرسال',
        'btn.delete': 'حذف',
        'btn.edit': 'تعديل',
        'btn.close': 'إغلاق',
        'btn.send': 'إرسال',
        'btn.remove': 'إزالة',
        'btn.add': 'إضافة',
        'btn.load': 'تحميل',
        'btn.clear': 'مسح',
        'btn.today': 'اليوم',
        'btn.logout': 'تسجيل الخروج',
        
        // Feed page
        'feed.title': 'موجزي',
        'feed.subtitle': 'شارك أفكارك وتواصل مع الآخرين',
        'feed.placeholder': 'ماذا يدور في ذهنك؟',
        'feed.calendar_title': 'متتبع النشاط اليومي',
        'feed.load_day': 'تحميل اليوم',
        'feed.save_day': 'حفظ اليوم',
        'feed.load_update': 'تحميل التحديث',
        'feed.save_update': 'حفظ التحديث',
        'feed.today': 'اليوم',
        'feed.selected_date': 'التاريخ المحدد',
        'feed.mood_notes': 'المزاج والملاحظات اليومية',
        'feed.how_feeling': 'كيف تشعر اليوم؟',
        'feed.select_mood': 'اختر المزاج...',
        'feed.daily_reflection': 'تأمل يومي:',
        'feed.reflection_placeholder': 'كيف كان يومك؟ أي أفكار أو مشاعر للتسجيل؟',
        'feed.posts_today': 'المنشورات اليوم',
        'feed.messages_sent': 'الرسائل المرسلة',
        'feed.comments_made': 'التعليقات المقدمة',
        'feed.activity_history': 'سجل نشاطك',
        'feed.loaded_activity': 'تم تحميل النشاط لـ',
        'feed.no_activity': 'لم يتم العثور على نشاط لهذا التاريخ',
        'feed.activity_saved': 'تم حفظ النشاط لـ',
        'feed.select_date': 'يرجى تحديد تاريخ',
        'feed.no_saved_activity': 'لا يوجد نشاط محفوظ بعد. ابدأ التتبع اليوم!',
        'feed.more_dates': 'تواريخ أخرى',
        
        // Calendar
        'calendar.prev': 'السابق',
        'calendar.next': 'التالي',
        'calendar.today': 'اليوم',
        'calendar.days': 'أيام',
        'calendar.month_year': '{month} {year}',
        
        // Visibility settings
        'visibility.general': 'عام',
        'visibility.close_friends': 'الأصدقاء المقربون',
        'visibility.family': 'العائلة',
        'visibility.private': 'خاص',
        
        // Alerts
        'alerts.title': 'الإشعارات',
        'alerts.no_alerts': 'لا توجد إشعارات بعد',
        'alerts.mark_read': 'وضع علامة كمقروء',
        'alerts.clear_all': 'مسح الكل',
        
        // Circles page
        'circles.title': 'دوائري',
        'circles.subtitle': 'نظم اتصالاتك في مجموعات ذات مغزى',
        'circles.search_placeholder': 'ابحث عن المستخدمين بالاسم أو البريد الإلكتروني...',
        'circles.general': 'عام',
        'circles.close_friends': 'الأصدقاء المقربون',
        'circles.family': 'العائلة',
        'circles.no_members': 'لا يوجد أعضاء بعد',
        'circles.add_to_circle': 'أضف إلى الدائرة',
        'circles.no_users_found': 'لم يتم العثور على مستخدمين',
        'circles.user_added': 'تمت الإضافة إلى',
        'circles.circle': 'دائرة!',
        'circles.remove_confirm': 'إزالة هذا المستخدم من الدائرة؟',
        'circles.user_removed': 'تمت إزالة المستخدم من الدائرة',
        
        // Messages page
        'messages.title': 'الرسائل',
        'messages.new': '+ جديد',
        'messages.select_conversation': 'حدد محادثة',
        'messages.no_conversations': 'لا توجد محادثات بعد',
        'messages.type_message': 'اكتب رسالة...',
        'messages.send': 'إرسال',
        'messages.search': 'البحث في المحادثات',
        'messages.search_placeholder': 'البحث عن رسائل...',
        'messages.no_messages': 'لا توجد رسائل بعد',
        'messages.start_conversation': 'لا توجد رسائل بعد. ابدأ المحادثة!',
        'messages.new_message': 'رسالة جديدة',
        'messages.select_recipient': 'حدد المستلم...',
        'messages.select_and_type': 'يرجى تحديد مستلم وإدخال رسالة',
        'messages.message_sent': 'تم إرسال الرسالة!',
        
        // Moods
        'mood.great': '😊 رائع',
        'mood.good': '🙂 جيد',
        'mood.okay': '😐 بخير',
        'mood.down': '😔 حزين',
        'mood.anxious': '😰 قلق',
        'mood.tired': '😴 متعب',
        'mood.frustrated': '😡 محبط',
        'mood.hopeful': '🤗 متفائل',
        'mood.happy': '😊 سعيد',
        'mood.calm': '😌 هادئ',
        'mood.sad': '😢 حزين',
        'mood.energetic': '🔥 نشيط',
        
        // Parameters page
        'parameters.title': 'المعاملات اليومية',
        'parameters.select_date': 'حدد التاريخ',
        'parameters.current_date': 'التاريخ الحالي:',
        'parameters.insights': 'الرؤى',
        'parameters.mood': 'المزاج',
        'parameters.mood_placeholder': 'كيف تشعر؟ (مثل: سعيد، هادئ، قلق، إلخ)',
        'parameters.sleep': 'النوم',
        'parameters.sleep_hours': 'ساعات',
        'parameters.exercise': 'التمرين',
        'parameters.exercise_placeholder': 'ما التمرين الذي قمت به؟ (مثل: الجري، اليوغا، الصالة الرياضية، المشي)',
        'parameters.anxiety': 'مستوى القلق',
        'parameters.anxiety_placeholder': 'صف مستوى قلقك (مثل: لا شيء، خفيف، متوسط، شديد)',
        'parameters.energy': 'مستوى الطاقة',
        'parameters.energy_placeholder': 'صف مستوى طاقتك (مثل: منخفض جدًا، منخفض، عادي، مرتفع، مرتفع جدًا)',
        'parameters.notes': 'ملاحظات',
        'parameters.notes_placeholder': 'أي ملاحظات أو أفكار إضافية لليوم...',
        'parameters.save': 'حفظ المعاملات',
        'parameters.load': 'تحميل المعاملات',
        'parameters.clear': 'مسح',
        'parameters.saved': 'تم حفظ المعاملات بنجاح',
        'parameters.loaded': 'تم تحميل المعاملات من',
        'parameters.no_saved': 'لا توجد معاملات محفوظة لهذا التاريخ',
        'parameters.cleared': 'تم مسح المعاملات',
        'parameters.today_label': 'اليوم',
        
        // Profile page
        'profile.title': 'ملفي الشخصي',
        'profile.loading': 'جارٍ التحميل...',
        'profile.completion': 'اكتمال الملف الشخصي:',
        'profile.about_me': 'عني',
        'profile.bio': 'السيرة الذاتية',
        'profile.bio_placeholder': 'أخبرنا عن نفسك...',
        'profile.professional': 'مهني',
        'profile.occupation': 'المهنة',
        'profile.occupation_placeholder': 'ماذا تعمل؟',
        'profile.goals_aspirations': 'الأهداف والطموحات',
        'profile.goals': 'أهدافي',
        'profile.my_goals': 'أهدافي',
        'profile.goals_placeholder': 'ما هي أهدافك الشخصية أو المهنية؟',
        'profile.interests_hobbies': 'الاهتمامات والهوايات',
        'profile.interests': 'الاهتمامات',
        'profile.interests_placeholder': 'ما الذي تهتم به؟',
        'profile.hobbies': 'الهوايات المفضلة',
        'profile.favorite_hobbies': 'الهوايات المفضلة',
        'profile.hobbies_placeholder': 'ماذا تحب أن تفعل في وقت فراغك؟',
        'profile.save_changes': 'حفظ التغييرات',
        'profile.cancel': 'إلغاء',
        'profile.updated': 'تم تحديث الملف الشخصي بنجاح!',
        
        // Days of week
        'day.sun': 'الأحد',
        'day.mon': 'الاثنين',
        'day.tue': 'الثلاثاء',
        'day.wed': 'الأربعاء',
        'day.thu': 'الخميس',
        'day.fri': 'الجمعة',
        'day.sat': 'السبت',
        
        // Months
        'month.january': 'يناير',
        'month.february': 'فبراير',
        'month.march': 'مارس',
        'month.april': 'أبريل',
        'month.may': 'مايو',
        'month.june': 'يونيو',
        'month.july': 'يوليو',
        'month.august': 'أغسطس',
        'month.september': 'سبتمبر',
        'month.october': 'أكتوبر',
        'month.november': 'نوفمبر',
        'month.december': 'ديسمبر',
        
        // Error messages
        'error.loading': 'خطأ في تحميل البيانات',
        'error.saving': 'خطأ في حفظ البيانات',
        'error.required': 'هذا الحقل مطلوب',
        'error.server': 'خطأ في الخادم. يرجى المحاولة مرة أخرى.',
        
        // Success messages
        'success.saved': 'تم الحفظ بنجاح',
        'success.updated': 'تم التحديث بنجاح',
        'success.deleted': 'تم الحذف بنجاح'
    },
    
    ru: {
        // Navigation & Menu
        'nav.logo': 'TheraSocial',
        'nav.home': 'Главная',
        'nav.about': 'О нас',
        'nav.support': 'Поддержка',
        'menu.feed': 'Лента',
        'menu.profile': 'Профиль',
        'menu.circles': 'Круги',
        'menu.messages': 'Сообщения',
        'menu.parameters': 'Параметры',
        'menu.logout': 'Выход',
        
        // Authentication
        'auth.welcome': 'Добро пожаловать в TheraSocial',
        'auth.subtitle': 'Общайтесь, делитесь и развивайтесь вместе',
        'auth.email': 'Электронная почта',
        'auth.email_placeholder': 'Введите ваш email',
        'auth.password': 'Пароль',
        'auth.password_placeholder': 'Введите ваш пароль',
        'auth.signin': 'Войти',
        'auth.signup': 'Регистрация',
        'auth.toggle_signup': 'Нет аккаунта? Зарегистрируйтесь',
        'auth.toggle_signin': 'Уже есть аккаунт? Войдите',
        'auth.forgot_password': 'Забыли пароль?',
        'auth.remember_me': 'Запомнить меня',
        'auth.or': 'ИЛИ',
        'auth.login_error': 'Неверный email или пароль',
        'auth.signup_success': 'Аккаунт успешно создан!',
        'auth.name': 'Полное имя',
        'auth.name_placeholder': 'Введите ваше полное имя',
        'auth.confirm_password': 'Подтвердите пароль',
        'auth.confirm_password_placeholder': 'Введите пароль ещё раз',
        
        // Common buttons
        'btn.signin': 'Войти',
        'btn.signup': 'Регистрация',
        'btn.save': 'Сохранить',
        'btn.cancel': 'Отмена',
        'btn.submit': 'Отправить',
        'btn.delete': 'Удалить',
        'btn.edit': 'Редактировать',
        'btn.close': 'Закрыть',
        'btn.send': 'Отправить',
        'btn.remove': 'Удалить',
        'btn.add': 'Добавить',
        'btn.load': 'Загрузить',
        'btn.clear': 'Очистить',
        'btn.today': 'Сегодня',
        'btn.logout': 'Выход',
        
        // Feed page
        'feed.title': 'Моя лента',
        'feed.subtitle': 'Делитесь мыслями и общайтесь с другими',
        'feed.placeholder': 'О чём вы думаете?',
        'feed.calendar_title': 'Трекер ежедневной активности',
        'feed.load_day': 'Загрузить день',
        'feed.save_day': 'Сохранить день',
        'feed.load_update': 'Загрузить обновление',
        'feed.save_update': 'Сохранить обновление',
        'feed.today': 'Сегодня',
        'feed.selected_date': 'Выбранная дата',
        'feed.mood_notes': 'Настроение и заметки',
        'feed.how_feeling': 'Как вы себя чувствуете сегодня?',
        'feed.select_mood': 'Выберите настроение...',
        'feed.daily_reflection': 'Ежедневное размышление:',
        'feed.reflection_placeholder': 'Как прошёл ваш день? Какие мысли или чувства записать?',
        'feed.posts_today': 'Записей сегодня',
        'feed.messages_sent': 'Отправлено сообщений',
        'feed.comments_made': 'Оставлено комментариев',
        'feed.activity_history': 'История вашей активности',
        'feed.loaded_activity': 'Загружена активность за',
        'feed.no_activity': 'Нет активности за эту дату',
        'feed.activity_saved': 'Активность сохранена за',
        'feed.select_date': 'Пожалуйста, выберите дату',
        'feed.no_saved_activity': 'Пока нет сохранённой активности. Начните отслеживание сегодня!',
        'feed.more_dates': 'больше дат',
        
        // Calendar
        'calendar.prev': 'Предыдущий',
        'calendar.next': 'Следующий',
        'calendar.today': 'Сегодня',
        'calendar.days': 'Дни',
        'calendar.month_year': '{month} {year}',
        
        // Visibility settings
        'visibility.general': 'Общий',
        'visibility.close_friends': 'Близкие друзья',
        'visibility.family': 'Семья',
        'visibility.private': 'Личное',
        
        // Alerts
        'alerts.title': 'Уведомления',
        'alerts.no_alerts': 'Пока нет уведомлений',
        'alerts.mark_read': 'Отметить как прочитанное',
        'alerts.clear_all': 'Очистить всё',
        
        // Circles page
        'circles.title': 'Мои круги',
        'circles.subtitle': 'Организуйте свои связи в значимые группы',
        'circles.search_placeholder': 'Поиск пользователей по имени или email...',
        'circles.general': 'Общий',
        'circles.close_friends': 'Близкие друзья',
        'circles.family': 'Семья',
        'circles.no_members': 'Пока нет участников',
        'circles.add_to_circle': 'Добавить в круг',
        'circles.no_users_found': 'Пользователи не найдены',
        'circles.user_added': 'добавлен в',
        'circles.circle': 'круг!',
        'circles.remove_confirm': 'Удалить этого пользователя из круга?',
        'circles.user_removed': 'Пользователь удалён из круга',
        
        // Messages page
        'messages.title': 'Сообщения',
        'messages.new': '+ Новое',
        'messages.select_conversation': 'Выберите разговор',
        'messages.no_conversations': 'Пока нет разговоров',
        'messages.type_message': 'Введите сообщение...',
        'messages.send': 'Отправить',
        'messages.search': 'Поиск по разговорам',
        'messages.search_placeholder': 'Поиск сообщений...',
        'messages.no_messages': 'Пока нет сообщений',
        'messages.start_conversation': 'Пока нет сообщений. Начните разговор!',
        'messages.new_message': 'Новое сообщение',
        'messages.select_recipient': 'Выберите получателя...',
        'messages.select_and_type': 'Пожалуйста, выберите получателя и введите сообщение',
        'messages.message_sent': 'Сообщение отправлено!',
        
        // Moods
        'mood.great': '😊 Отлично',
        'mood.good': '🙂 Хорошо',
        'mood.okay': '😐 Нормально',
        'mood.down': '😔 Подавленный',
        'mood.anxious': '😰 Встревоженный',
        'mood.tired': '😴 Усталый',
        'mood.frustrated': '😡 Расстроенный',
        'mood.hopeful': '🤗 Полный надежд',
        'mood.happy': '😊 Счастливый',
        'mood.calm': '😌 Спокойный',
        'mood.sad': '😢 Грустный',
        'mood.energetic': '🔥 Энергичный',
        
        // Parameters page
        'parameters.title': 'Ежедневные параметры',
        'parameters.select_date': 'Выберите дату',
        'parameters.current_date': 'Текущая дата:',
        'parameters.insights': 'Аналитика',
        'parameters.mood': 'Настроение',
        'parameters.mood_placeholder': 'Как вы себя чувствуете? (например, Счастливый, Спокойный, Встревоженный и т.д.)',
        'parameters.sleep': 'Сон',
        'parameters.sleep_hours': 'Часов',
        'parameters.exercise': 'Упражнения',
        'parameters.exercise_placeholder': 'Какие упражнения вы делали? (например, Бег, Йога, Зал, Ходьба)',
        'parameters.anxiety': 'Уровень тревожности',
        'parameters.anxiety_placeholder': 'Опишите уровень тревожности (например, Нет, Слабая, Умеренная, Сильная)',
        'parameters.energy': 'Уровень энергии',
        'parameters.energy_placeholder': 'Опишите уровень энергии (например, Очень низкий, Низкий, Нормальный, Высокий, Очень высокий)',
        'parameters.notes': 'Заметки',
        'parameters.notes_placeholder': 'Дополнительные заметки или мысли на сегодня...',
        'parameters.save': 'Сохранить параметры',
        'parameters.load': 'Загрузить параметры',
        'parameters.clear': 'Очистить',
        'parameters.saved': 'Параметры успешно сохранены',
        'parameters.loaded': 'Загружены параметры от',
        'parameters.no_saved': 'Нет сохранённых параметров для этой даты',
        'parameters.cleared': 'Параметры очищены',
        'parameters.today_label': 'Сегодня',
        
        // Profile page
        'profile.title': 'Мой профиль',
        'profile.loading': 'Загрузка...',
        'profile.completion': 'Заполнение профиля:',
        'profile.about_me': 'О себе',
        'profile.bio': 'Биография',
        'profile.bio_placeholder': 'Расскажите о себе...',
        'profile.professional': 'Профессиональная информация',
        'profile.occupation': 'Род занятий',
        'profile.occupation_placeholder': 'Чем вы занимаетесь?',
        'profile.goals_aspirations': 'Цели и стремления',
        'profile.goals': 'Мои цели',
        'profile.my_goals': 'Мои цели',
        'profile.goals_placeholder': 'Каковы ваши личные или профессиональные цели?',
        'profile.interests_hobbies': 'Интересы и хобби',
        'profile.interests': 'Интересы',
        'profile.interests_placeholder': 'Чем вы интересуетесь?',
        'profile.hobbies': 'Любимые хобби',
        'profile.favorite_hobbies': 'Любимые хобби',
        'profile.hobbies_placeholder': 'Чем вы любите заниматься в свободное время?',
        'profile.save_changes': 'Сохранить изменения',
        'profile.cancel': 'Отмена',
        'profile.updated': 'Профиль успешно обновлён!',
        
        // Days of week
        'day.sun': 'Вс',
        'day.mon': 'Пн',
        'day.tue': 'Вт',
        'day.wed': 'Ср',
        'day.thu': 'Чт',
        'day.fri': 'Пт',
        'day.sat': 'Сб',
        
        // Months
        'month.january': 'Январь',
        'month.february': 'Февраль',
        'month.march': 'Март',
        'month.april': 'Апрель',
        'month.may': 'Май',
        'month.june': 'Июнь',
        'month.july': 'Июль',
        'month.august': 'Август',
        'month.september': 'Сентябрь',
        'month.october': 'Октябрь',
        'month.november': 'Ноябрь',
        'month.december': 'Декабрь',
        
        // Error messages
        'error.loading': 'Ошибка загрузки данных',
        'error.saving': 'Ошибка сохранения данных',
        'error.required': 'Это поле обязательно',
        'error.server': 'Ошибка сервера. Попробуйте ещё раз.',
        
        // Success messages
        'success.saved': 'Успешно сохранено',
        'success.updated': 'Успешно обновлено',
        'success.deleted': 'Успешно удалено'
    }
};

// Language detection and initialization
function detectBrowserLanguage() {
    const browserLang = navigator.language || navigator.userLanguage;
    const langCode = browserLang.split('-')[0]; // Get 'en' from 'en-US'
    
    // Check if we support this language
    const supportedLanguages = ['en', 'he', 'ar', 'ru'];
    return supportedLanguages.includes(langCode) ? langCode : 'en';
}

function getCurrentLanguage() {
    // Priority: 1. Stored preference, 2. Browser language, 3. Default English
    return localStorage.getItem('selectedLanguage') || detectBrowserLanguage();
}

function setLanguage(lang) {
    localStorage.setItem('selectedLanguage', lang);
    applyLanguage(lang);
    
    // Update HTML dir and lang attributes for RTL languages
    if (lang === 'he' || lang === 'ar') {
        document.documentElement.setAttribute('dir', 'rtl');
        document.documentElement.setAttribute('lang', lang);
    } else {
        document.documentElement.setAttribute('dir', 'ltr');
        document.documentElement.setAttribute('lang', lang);
    }
    
    // Sync with backend if user is logged in
    syncLanguageWithBackend(lang);
}

async function syncLanguageWithBackend(lang) {
    try {
        const response = await fetch('/api/user/language', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                preferred_language: lang
            })
        });
        // Don't throw on 401 - user just not logged in yet
        if (response.ok) {
            console.log('Language preference synced with backend');
        }
    } catch (error) {
        // Silently fail - language is still saved in localStorage
        console.log('Could not sync language preference with server');
    }
}

function translate(key, lang = null) {
    const currentLang = lang || getCurrentLanguage();
    return translations[currentLang]?.[key] || translations['en'][key] || key;
}

// Alias 't' for translate to support window.i18n.t() calls
const t = translate;

function applyLanguage(lang) {
    // Translate all elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        const translatedText = translate(key, lang);
        
        if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
            element.placeholder = translatedText;
        } else {
            element.textContent = translatedText;
        }
    });
    
    // Translate all elements with data-i18n-placeholder attribute
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        const key = element.getAttribute('data-i18n-placeholder');
        element.placeholder = translate(key, lang);
    });
    
    // Update language selector if it exists
    const langSelector = document.getElementById('languageSelector');
    if (langSelector) {
        langSelector.value = lang;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    const currentLang = getCurrentLanguage();
    setLanguage(currentLang);
    
    // Set up language selector if it exists
    const langSelector = document.getElementById('languageSelector');
    if (langSelector) {
        langSelector.value = currentLang;
        langSelector.addEventListener('change', function() {
            setLanguage(this.value);
            // Reload dynamic content if needed
            if (typeof loadDynamicContent === 'function') {
                loadDynamicContent();
            }
        });
    }
});

// Export for use in other scripts - includes both 'translate' and 't' as alias
if (typeof window !== 'undefined') {
    window.i18n = {
        translate,
        t,  // ADD THIS - alias for translate
        getCurrentLanguage,
        setLanguage,
        detectBrowserLanguage,
        translations
    };
}
