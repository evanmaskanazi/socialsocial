// Language detection and translation system for Thera Social
const translations = {
    en: {
        // Navigation
        'nav.logo': '🧠 Thera Social',
        'nav.home': 'Home',
        'nav.about': 'About',
        'nav.support': 'Support',
        'nav.logout': 'Logout',
        
        // Common buttons
        'btn.save': 'Save',
        'btn.cancel': 'Cancel',
        'btn.submit': 'Submit',
        'btn.delete': 'Delete',
        'btn.edit': 'Edit',
        'btn.close': 'Close',
        'btn.send': 'Send',
        'btn.load': 'Load',
        'btn.back': 'Back to Home',
        'btn.signin': 'Sign In',
        'btn.signup': 'Sign Up',
        'btn.getstarted': 'Get Started',
        
        // Auth page
        'auth.welcome': 'Welcome Back',
        'auth.create': 'Create Account',
        'auth.email': 'Email',
        'auth.password': 'Password',
        'auth.username': 'Username',
        'auth.username_placeholder': 'Choose a username',
        'auth.toggle_signup': 'New here? Create an account',
        'auth.toggle_signin': 'Already have an account? Sign in',
        
        // Feed page
        'feed.title': 'Your Feed Journal',
        'feed.subtitle': 'Save your thoughts for each day. Select a date from the calendar, write your update, and save it. Green dots show dates with saved entries.',
        'feed.placeholder': 'How are you feeling today?',
        'feed.selected_date': 'Selected Date:',
        'feed.today': 'Today',
        'feed.load_update': 'Load Update',
        'feed.save_update': 'Save Update',
        'feed.no_posts': 'No posts yet',
        
        // Visibility options
        'visibility.general': 'General',
        'visibility.close_friends': 'Close Friends',
        'visibility.family': 'Family',
        'visibility.private': 'Private',
        
        // Profile page
        'profile.title': 'Your Profile',
        'profile.bio': 'Bio',
        'profile.bio_placeholder': 'Tell us about yourself...',
        'profile.interests': 'Interests',
        'profile.interests_placeholder': 'What are you interested in?',
        'profile.occupation': 'Occupation',
        'profile.occupation_placeholder': 'What do you do?',
        'profile.goals': 'Goals',
        'profile.goals_placeholder': 'What are your personal or professional goals?',
        'profile.hobbies': 'Favorite Hobbies',
        'profile.hobbies_placeholder': 'What do you love to do in your free time?',
        'profile.save': 'Save Profile',
        
        // Circles page
        'circles.title': 'Your Circles',
        'circles.search_placeholder': 'Search users to add to circles...',
        'circles.general': '💥 General',
        'circles.close_friends': '❤️ Close Friends',
        'circles.family': '👨‍👩‍👧‍👦 Family',
        'circles.no_members': 'No members yet',
        'circles.remove': 'Remove',
        'circles.add_to': 'Add to circle...',
        'circles.no_users': 'No users found',
        
        // Messages page
        'messages.title': 'Messages',
        'messages.search_placeholder': 'Search users to message...',
        'messages.select_conversation': 'Select a conversation',
        'messages.no_conversations': 'No conversations yet',
        'messages.no_messages': 'No messages yet. Start the conversation!',
        'messages.type_message': 'Type a message...',
        'messages.you': 'You: ',
        
        // Parameters page
        'parameters.title': 'Wellness Parameters',
        'parameters.selected_date': 'Selected Date:',
        'parameters.mood': 'Mood',
        'parameters.mood_placeholder': 'e.g., Happy, Calm, Anxious',
        'parameters.sleep': 'Sleep',
        'parameters.sleep_placeholder': 'Hours',
        'parameters.sleep_hours': 'Hours',
        'parameters.exercise': 'Exercise',
        'parameters.exercise_placeholder': 'e.g., Running, Yoga, Gym',
        'parameters.anxiety': 'Anxiety',
        'parameters.anxiety_placeholder': 'e.g., None, Mild, Moderate',
        'parameters.energy': 'Energy',
        'parameters.energy_placeholder': 'e.g., Low, Normal, High',
        'parameters.notes': 'Notes',
        'parameters.notes_placeholder': 'Additional notes...',
        'parameters.save': 'Save Parameters',
        'parameters.load': 'Load Parameters',
        'parameters.insights': 'Insights',
        
        // Sidebar menu
        'menu.feed': '📱 Feed',
        'menu.profile': '👤 Profile',
        'menu.circles': '👥 Circles',
        'menu.messages': '💬 Messages',
        'menu.parameters': '📊 Parameters',
        
        // Alerts
        'alerts.title': 'Alerts',
        'alerts.no_alerts': 'No new alerts',
        
        // About page
        'about.title': 'About Thera Social',
        'about.subtitle': 'Your safe space for wellness, connection, and personal growth',
        'about.privacy_title': 'Privacy First',
        'about.privacy_desc': 'Your wellness journey is private and secure. Share only what you\'re comfortable with.',
        'about.track_title': 'Track Progress',
        'about.track_desc': 'Monitor your wellness parameters and see your growth over time with insights.',
        'about.community_title': 'Supportive Community',
        'about.community_desc': 'Connect with others on similar journeys in a judgment-free environment.',
        'about.communication_title': 'Safe Communication',
        'about.communication_desc': 'Private messaging and circles let you control who sees your content.',
        'about.goals_title': 'Goal Setting',
        'about.goals_desc': 'Set and track personal goals with community support and accountability.',
        'about.checkin_title': 'Daily Check-ins',
        'about.checkin_desc': 'Regular parameter tracking helps you understand patterns and triggers.',
        
        // Support page
        'support.title': 'Support Center',
        'support.subtitle': 'We\'re here to help you on your wellness journey',
        'support.faq_title': 'Frequently Asked Questions',
        'support.faq1_q': 'How do I track my wellness parameters?',
        'support.faq1_a': 'Navigate to the Parameters tab in your dashboard. You can input daily values for mood, sleep, exercise, anxiety, and energy levels. Use the calendar to save and load parameters for different dates.',
        'support.faq2_q': 'What are Circles?',
        'support.faq2_a': 'Circles allow you to organize your connections into groups: General, Close Friends, and Family. You can control who sees your posts based on these circles.',
        'support.faq3_q': 'How do I update my profile?',
        'support.faq3_a': 'Go to the Profile tab to update your bio, interests, occupation, goals, and favorite hobbies. These help others understand you better.',
        'support.faq4_q': 'Is my data private?',
        'support.faq4_a': 'Yes! We take privacy seriously. Your wellness data is encrypted and only visible to you unless you choose to share it.',
        'support.contact_title': 'Contact Support',
        'support.subject': 'Subject',
        'support.message': 'Message',
        'support.send': 'Send Message',
        
        // Calendar
        'calendar.prev': '←',
        'calendar.next': '→',
        'calendar.days': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
        'calendar.months': ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
        
        // Messages
        'msg.success': 'Success!',
        'msg.error': 'Error',
        'msg.saved': 'Saved successfully!',
        'msg.loaded': 'Loaded successfully!',
        'msg.deleted': 'Deleted successfully!',
        'msg.sent': 'Message sent!',
    },
    
    he: {
        // Navigation
        'nav.logo': '🧠 תרה סושיאל',
        'nav.home': 'בית',
        'nav.about': 'אודות',
        'nav.support': 'תמיכה',
        'nav.logout': 'יציאה',
        
        // Common buttons
        'btn.save': 'שמירה',
        'btn.cancel': 'ביטול',
        'btn.submit': 'שליחה',
        'btn.delete': 'מחיקה',
        'btn.edit': 'עריכה',
        'btn.close': 'סגירה',
        'btn.send': 'שלח',
        'btn.load': 'טעינה',
        'btn.back': 'חזרה לבית',
        'btn.signin': 'כניסה',
        'btn.signup': 'הרשמה',
        'btn.getstarted': 'התחל',
        
        // Auth page
        'auth.welcome': 'ברוכים השבים',
        'auth.create': 'יצירת חשבון',
        'auth.email': 'אימייל',
        'auth.password': 'סיסמה',
        'auth.username': 'שם משתמש',
        'auth.username_placeholder': 'בחר שם משתמש',
        'auth.toggle_signup': 'חדש כאן? צור חשבון',
        'auth.toggle_signin': 'כבר יש לך חשבון? התחבר',
        
        // Feed page
        'feed.title': 'יומן הפיד שלך',
        'feed.subtitle': 'שמור את המחשבות שלך לכל יום. בחר תאריך מהלוח, כתוב את העדכון שלך ושמור אותו. נקודות ירוקות מציגות תאריכים עם רשומות שמורות.',
        'feed.placeholder': 'איך אתה מרגיש היום?',
        'feed.selected_date': 'תאריך נבחר:',
        'feed.today': 'היום',
        'feed.load_update': 'טען עדכון',
        'feed.save_update': 'שמור עדכון',
        'feed.no_posts': 'אין עדיין פוסטים',
        
        // Visibility options
        'visibility.general': 'כללי',
        'visibility.close_friends': 'חברים קרובים',
        'visibility.family': 'משפחה',
        'visibility.private': 'פרטי',
        
        // Profile page
        'profile.title': 'הפרופיל שלך',
        'profile.bio': 'ביוגרפיה',
        'profile.bio_placeholder': 'ספר לנו על עצמך...',
        'profile.interests': 'תחומי עניין',
        'profile.interests_placeholder': 'במה אתה מתעניין?',
        'profile.occupation': 'עיסוק',
        'profile.occupation_placeholder': 'מה אתה עושה?',
        'profile.goals': 'מטרות',
        'profile.goals_placeholder': 'מהן המטרות האישיות או המקצועיות שלך?',
        'profile.hobbies': 'תחביבים מועדפים',
        'profile.hobbies_placeholder': 'מה אתה אוהב לעשות בזמן הפנוי?',
        'profile.save': 'שמור פרופיל',
        
        // Circles page
        'circles.title': 'המעגלים שלך',
        'circles.search_placeholder': 'חפש משתמשים להוספה למעגלים...',
        'circles.general': '💥 כללי',
        'circles.close_friends': '❤️ חברים קרובים',
        'circles.family': '👨‍👩‍👧‍👦 משפחה',
        'circles.no_members': 'אין עדיין חברים',
        'circles.remove': 'הסר',
        'circles.add_to': 'הוסף למעגל...',
        'circles.no_users': 'לא נמצאו משתמשים',
        
        // Messages page
        'messages.title': 'הודעות',
        'messages.search_placeholder': 'חפש משתמשים לשליחת הודעות...',
        'messages.select_conversation': 'בחר שיחה',
        'messages.no_conversations': 'אין עדיין שיחות',
        'messages.no_messages': 'אין עדיין הודעות. התחל את השיחה!',
        'messages.type_message': 'הקלד הודעה...',
        'messages.you': 'אתה: ',
        
        // Parameters page
        'parameters.title': 'פרמטרי בריאות',
        'parameters.selected_date': 'תאריך נבחר:',
        'parameters.mood': 'מצב רוח',
        'parameters.mood_placeholder': 'לדוגמה: שמח, רגוע, חרד',
        'parameters.sleep': 'שינה',
        'parameters.sleep_placeholder': 'שעות',
        'parameters.sleep_hours': 'שעות',
        'parameters.exercise': 'פעילות גופנית',
        'parameters.exercise_placeholder': 'לדוגמה: ריצה, יוגה, חדר כושר',
        'parameters.anxiety': 'חרדה',
        'parameters.anxiety_placeholder': 'לדוגמה: ללא, קלה, בינונית',
        'parameters.energy': 'אנרגיה',
        'parameters.energy_placeholder': 'לדוגמה: נמוכה, רגילה, גבוהה',
        'parameters.notes': 'הערות',
        'parameters.notes_placeholder': 'הערות נוספות...',
        'parameters.save': 'שמור פרמטרים',
        'parameters.load': 'טען פרמטרים',
        'parameters.insights': 'תובנות',
        
        // Sidebar menu
        'menu.feed': '📱 פיד',
        'menu.profile': '👤 פרופיל',
        'menu.circles': '👥 מעגלים',
        'menu.messages': '💬 הודעות',
        'menu.parameters': '📊 פרמטרים',
        
        // Alerts
        'alerts.title': 'התראות',
        'alerts.no_alerts': 'אין התראות חדשות',
        
        // About page
        'about.title': 'אודות תרה סושיאל',
        'about.subtitle': 'המרחב הבטוח שלך לבריאות, חיבור וצמיחה אישית',
        'about.privacy_title': 'פרטיות במקום הראשון',
        'about.privacy_desc': 'מסע הבריאות שלך הוא פרטי ומאובטח. שתף רק את מה שנוח לך.',
        'about.track_title': 'מעקב אחר התקדמות',
        'about.track_desc': 'עקוב אחר פרמטרי הבריאות שלך וראה את הצמיחה שלך לאורך זמן עם תובנות.',
        'about.community_title': 'קהילה תומכת',
        'about.community_desc': 'התחבר לאחרים במסעות דומים בסביבה ללא שיפוטיות.',
        'about.communication_title': 'תקשורת בטוחה',
        'about.communication_desc': 'הודעות פרטיות ומעגלים מאפשרים לך לשלוט מי רואה את התוכן שלך.',
        'about.goals_title': 'הגדרת מטרות',
        'about.goals_desc': 'הגדר ועקוב אחר מטרות אישיות עם תמיכה ואחריות קהילתית.',
        'about.checkin_title': 'צ\'ק-אין יומי',
        'about.checkin_desc': 'מעקב קבוע אחר פרמטרים עוזר לך להבין דפוסים וטריגרים.',
        
        // Support page
        'support.title': 'מרכז תמיכה',
        'support.subtitle': 'אנחנו כאן לעזור לך במסע הבריאות שלך',
        'support.faq_title': 'שאלות נפוצות',
        'support.faq1_q': 'איך אני עוקב אחר פרמטרי הבריאות שלי?',
        'support.faq1_a': 'נווט לכרטיסיית פרמטרים בלוח הבקרה שלך. אתה יכול להזין ערכים יומיים עבור מצב רוח, שינה, פעילות גופנית, חרדה ורמות אנרגיה. השתמש בלוח השנה לשמירה וטעינת פרמטרים לתאריכים שונים.',
        'support.faq2_q': 'מה הם מעגלים?',
        'support.faq2_a': 'מעגלים מאפשרים לך לארגן את החיבורים שלך לקבוצות: כללי, חברים קרובים ומשפחה. אתה יכול לשלוט מי רואה את הפוסטים שלך על בסיס מעגלים אלה.',
        'support.faq3_q': 'איך אני מעדכן את הפרופיל שלי?',
        'support.faq3_a': 'עבור לכרטיסיית פרופיל כדי לעדכן את הביוגרפיה, תחומי עניין, עיסוק, מטרות ותחביבים מועדפים שלך. אלה עוזרים לאחרים להבין אותך טוב יותר.',
        'support.faq4_q': 'האם הנתונים שלי פרטיים?',
        'support.faq4_a': 'כן! אנחנו לוקחים פרטיות ברצינות. נתוני הבריאות שלך מוצפנים ונראים רק לך אלא אם כן תבחר לשתף אותם.',
        'support.contact_title': 'צור קשר עם תמיכה',
        'support.subject': 'נושא',
        'support.message': 'הודעה',
        'support.send': 'שלח הודעה',
        
        // Calendar
        'calendar.prev': '→',
        'calendar.next': '←',
        'calendar.days': ['א\'', 'ב\'', 'ג\'', 'ד\'', 'ה\'', 'ו\'', 'ש\''],
        'calendar.months': ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני', 'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר'],
        
        // Messages
        'msg.success': 'הצלחה!',
        'msg.error': 'שגיאה',
        'msg.saved': 'נשמר בהצלחה!',
        'msg.loaded': 'נטען בהצלחה!',
        'msg.deleted': 'נמחק בהצלחה!',
        'msg.sent': 'ההודעה נשלחה!',
    },
    
    ar: {
        // Navigation
        'nav.logo': '🧠 تيرا سوشيال',
        'nav.home': 'الرئيسية',
        'nav.about': 'حول',
        'nav.support': 'الدعم',
        'nav.logout': 'تسجيل خروج',
        
        // Common buttons
        'btn.save': 'حفظ',
        'btn.cancel': 'إلغاء',
        'btn.submit': 'إرسال',
        'btn.delete': 'حذف',
        'btn.edit': 'تعديل',
        'btn.close': 'إغلاق',
        'btn.send': 'إرسال',
        'btn.load': 'تحميل',
        'btn.back': 'العودة للرئيسية',
        'btn.signin': 'تسجيل دخول',
        'btn.signup': 'إنشاء حساب',
        'btn.getstarted': 'ابدأ',
        
        // Auth page
        'auth.welcome': 'مرحباً بعودتك',
        'auth.create': 'إنشاء حساب',
        'auth.email': 'البريد الإلكتروني',
        'auth.password': 'كلمة المرور',
        'auth.username': 'اسم المستخدم',
        'auth.username_placeholder': 'اختر اسم مستخدم',
        'auth.toggle_signup': 'جديد هنا؟ إنشاء حساب',
        'auth.toggle_signin': 'هل لديك حساب؟ تسجيل الدخول',
        
        // Feed page
        'feed.title': 'مجلة الأخبار الخاصة بك',
        'feed.subtitle': 'احفظ أفكارك لكل يوم. حدد تاريخاً من التقويم، اكتب تحديثك واحفظه. النقاط الخضراء تُظهر التواريخ ذات الإدخالات المحفوظة.',
        'feed.placeholder': 'كيف تشعر اليوم؟',
        'feed.selected_date': 'التاريخ المحدد:',
        'feed.today': 'اليوم',
        'feed.load_update': 'تحميل التحديث',
        'feed.save_update': 'حفظ التحديث',
        'feed.no_posts': 'لا توجد منشورات حتى الآن',
        
        // Visibility options
        'visibility.general': 'عام',
        'visibility.close_friends': 'الأصدقاء المقربين',
        'visibility.family': 'العائلة',
        'visibility.private': 'خاص',
        
        // Profile page
        'profile.title': 'ملفك الشخصي',
        'profile.bio': 'السيرة الذاتية',
        'profile.bio_placeholder': 'أخبرنا عن نفسك...',
        'profile.interests': 'الاهتمامات',
        'profile.interests_placeholder': 'ما الذي تهتم به؟',
        'profile.occupation': 'المهنة',
        'profile.occupation_placeholder': 'ماذا تعمل؟',
        'profile.goals': 'الأهداف',
        'profile.goals_placeholder': 'ما هي أهدافك الشخصية أو المهنية؟',
        'profile.hobbies': 'الهوايات المفضلة',
        'profile.hobbies_placeholder': 'ماذا تحب أن تفعل في وقت فراغك؟',
        'profile.save': 'حفظ الملف الشخصي',
        
        // Circles page
        'circles.title': 'دوائرك',
        'circles.search_placeholder': 'ابحث عن المستخدمين لإضافتهم إلى الدوائر...',
        'circles.general': '💥 عام',
        'circles.close_friends': '❤️ الأصدقاء المقربين',
        'circles.family': '👨‍👩‍👧‍👦 العائلة',
        'circles.no_members': 'لا يوجد أعضاء بعد',
        'circles.remove': 'إزالة',
        'circles.add_to': 'إضافة إلى الدائرة...',
        'circles.no_users': 'لم يتم العثور على مستخدمين',
        
        // Messages page
        'messages.title': 'الرسائل',
        'messages.search_placeholder': 'ابحث عن المستخدمين لإرسال رسائل...',
        'messages.select_conversation': 'حدد محادثة',
        'messages.no_conversations': 'لا توجد محادثات بعد',
        'messages.no_messages': 'لا توجد رسائل بعد. ابدأ المحادثة!',
        'messages.type_message': 'اكتب رسالة...',
        'messages.you': 'أنت: ',
        
        // Parameters page
        'parameters.title': 'معايير الصحة',
        'parameters.selected_date': 'التاريخ المحدد:',
        'parameters.mood': 'المزاج',
        'parameters.mood_placeholder': 'مثلاً: سعيد، هادئ، قلق',
        'parameters.sleep': 'النوم',
        'parameters.sleep_placeholder': 'ساعات',
        'parameters.sleep_hours': 'ساعات',
        'parameters.exercise': 'التمرين',
        'parameters.exercise_placeholder': 'مثلاً: الجري، اليوغا، صالة الألعاب',
        'parameters.anxiety': 'القلق',
        'parameters.anxiety_placeholder': 'مثلاً: لا شيء، خفيف، متوسط',
        'parameters.energy': 'الطاقة',
        'parameters.energy_placeholder': 'مثلاً: منخفضة، عادية، عالية',
        'parameters.notes': 'ملاحظات',
        'parameters.notes_placeholder': 'ملاحظات إضافية...',
        'parameters.save': 'حفظ المعايير',
        'parameters.load': 'تحميل المعايير',
        'parameters.insights': 'رؤى',
        
        // Sidebar menu
        'menu.feed': '📱 الأخبار',
        'menu.profile': '👤 الملف الشخصي',
        'menu.circles': '👥 الدوائر',
        'menu.messages': '💬 الرسائل',
        'menu.parameters': '📊 المعايير',
        
        // Alerts
        'alerts.title': 'التنبيهات',
        'alerts.no_alerts': 'لا توجد تنبيهات جديدة',
        
        // About page
        'about.title': 'حول تيرا سوشيال',
        'about.subtitle': 'مساحتك الآمنة للصحة والتواصل والنمو الشخصي',
        'about.privacy_title': 'الخصوصية أولاً',
        'about.privacy_desc': 'رحلة الصحة الخاصة بك خاصة وآمنة. شارك فقط ما تشعر بالراحة تجاهه.',
        'about.track_title': 'تتبع التقدم',
        'about.track_desc': 'راقب معايير الصحة الخاصة بك وشاهد نموك مع مرور الوقت مع رؤى.',
        'about.community_title': 'مجتمع داعم',
        'about.community_desc': 'تواصل مع الآخرين في رحلات مماثلة في بيئة خالية من الأحكام.',
        'about.communication_title': 'اتصال آمن',
        'about.communication_desc': 'الرسائل الخاصة والدوائر تتيح لك التحكم في من يرى محتواك.',
        'about.goals_title': 'تحديد الأهداف',
        'about.goals_desc': 'حدد وتتبع الأهداف الشخصية مع دعم المجتمع والمساءلة.',
        'about.checkin_title': 'تسجيلات يومية',
        'about.checkin_desc': 'التتبع المنتظم للمعايير يساعدك على فهم الأنماط والمحفزات.',
        
        // Support page
        'support.title': 'مركز الدعم',
        'support.subtitle': 'نحن هنا لمساعدتك في رحلة الصحة الخاصة بك',
        'support.faq_title': 'الأسئلة الشائعة',
        'support.faq1_q': 'كيف أتتبع معايير الصحة الخاصة بي؟',
        'support.faq1_a': 'انتقل إلى علامة التبويب المعايير في لوحة التحكم الخاصة بك. يمكنك إدخال القيم اليومية للمزاج والنوم والتمرين والقلق ومستويات الطاقة. استخدم التقويم لحفظ وتحميل المعايير لتواريخ مختلفة.',
        'support.faq2_q': 'ما هي الدوائر؟',
        'support.faq2_a': 'تتيح لك الدوائر تنظيم اتصالاتك في مجموعات: عام، أصدقاء مقربين، وعائلة. يمكنك التحكم في من يرى منشوراتك بناءً على هذه الدوائر.',
        'support.faq3_q': 'كيف أقوم بتحديث ملفي الشخصي؟',
        'support.faq3_a': 'انتقل إلى علامة التبويب الملف الشخصي لتحديث سيرتك الذاتية والاهتمامات والمهنة والأهداف والهوايات المفضلة. هذه تساعد الآخرين على فهمك بشكل أفضل.',
        'support.faq4_q': 'هل بياناتي خاصة؟',
        'support.faq4_a': 'نعم! نحن نأخذ الخصوصية على محمل الجد. بيانات الصحة الخاصة بك مشفرة ومرئية فقط لك ما لم تختر مشاركتها.',
        'support.contact_title': 'اتصل بالدعم',
        'support.subject': 'الموضوع',
        'support.message': 'الرسالة',
        'support.send': 'إرسال رسالة',
        
        // Calendar
        'calendar.prev': '→',
        'calendar.next': '←',
        'calendar.days': ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'],
        'calendar.months': ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'],
        
        // Messages
        'msg.success': 'نجاح!',
        'msg.error': 'خطأ',
        'msg.saved': 'تم الحفظ بنجاح!',
        'msg.loaded': 'تم التحميل بنجاح!',
        'msg.deleted': 'تم الحذف بنجاح!',
        'msg.sent': 'تم إرسال الرسالة!',
    },
    
    ru: {
        // Navigation
        'nav.logo': '🧠 Тера Социал',
        'nav.home': 'Главная',
        'nav.about': 'О нас',
        'nav.support': 'Поддержка',
        'nav.logout': 'Выход',
        
        // Common buttons
        'btn.save': 'Сохранить',
        'btn.cancel': 'Отмена',
        'btn.submit': 'Отправить',
        'btn.delete': 'Удалить',
        'btn.edit': 'Редактировать',
        'btn.close': 'Закрыть',
        'btn.send': 'Отправить',
        'btn.load': 'Загрузить',
        'btn.back': 'Вернуться на главную',
        'btn.signin': 'Войти',
        'btn.signup': 'Регистрация',
        'btn.getstarted': 'Начать',
        
        // Auth page
        'auth.welcome': 'С возвращением',
        'auth.create': 'Создать аккаунт',
        'auth.email': 'Электронная почта',
        'auth.password': 'Пароль',
        'auth.username': 'Имя пользователя',
        'auth.username_placeholder': 'Выберите имя пользователя',
        'auth.toggle_signup': 'Новый пользователь? Создайте аккаунт',
        'auth.toggle_signin': 'Уже есть аккаунт? Войти',
        
        // Feed page
        'feed.title': 'Ваш журнал новостей',
        'feed.subtitle': 'Сохраняйте свои мысли за каждый день. Выберите дату в календаре, напишите обновление и сохраните его. Зеленые точки показывают даты с сохраненными записями.',
        'feed.placeholder': 'Как вы себя чувствуете сегодня?',
        'feed.selected_date': 'Выбранная дата:',
        'feed.today': 'Сегодня',
        'feed.load_update': 'Загрузить обновление',
        'feed.save_update': 'Сохранить обновление',
        'feed.no_posts': 'Пока нет постов',
        
        // Visibility options
        'visibility.general': 'Общее',
        'visibility.close_friends': 'Близкие друзья',
        'visibility.family': 'Семья',
        'visibility.private': 'Личное',
        
        // Profile page
        'profile.title': 'Ваш профиль',
        'profile.bio': 'Биография',
        'profile.bio_placeholder': 'Расскажите о себе...',
        'profile.interests': 'Интересы',
        'profile.interests_placeholder': 'Чем вы интересуетесь?',
        'profile.occupation': 'Род занятий',
        'profile.occupation_placeholder': 'Чем вы занимаетесь?',
        'profile.goals': 'Цели',
        'profile.goals_placeholder': 'Каковы ваши личные или профессиональные цели?',
        'profile.hobbies': 'Любимые хобби',
        'profile.hobbies_placeholder': 'Что вы любите делать в свободное время?',
        'profile.save': 'Сохранить профиль',
        
        // Circles page
        'circles.title': 'Ваши круги',
        'circles.search_placeholder': 'Поиск пользователей для добавления в круги...',
        'circles.general': '💥 Общий',
        'circles.close_friends': '❤️ Близкие друзья',
        'circles.family': '👨‍👩‍👧‍👦 Семья',
        'circles.no_members': 'Пока нет участников',
        'circles.remove': 'Удалить',
        'circles.add_to': 'Добавить в круг...',
        'circles.no_users': 'Пользователи не найдены',
        
        // Messages page
        'messages.title': 'Сообщения',
        'messages.search_placeholder': 'Поиск пользователей для отправки сообщений...',
        'messages.select_conversation': 'Выберите беседу',
        'messages.no_conversations': 'Пока нет бесед',
        'messages.no_messages': 'Пока нет сообщений. Начните беседу!',
        'messages.type_message': 'Введите сообщение...',
        'messages.you': 'Вы: ',
        
        // Parameters page
        'parameters.title': 'Параметры здоровья',
        'parameters.selected_date': 'Выбранная дата:',
        'parameters.mood': 'Настроение',
        'parameters.mood_placeholder': 'напр.: Счастлив, Спокоен, Тревожен',
        'parameters.sleep': 'Сон',
        'parameters.sleep_placeholder': 'Часы',
        'parameters.sleep_hours': 'Часы',
        'parameters.exercise': 'Упражнения',
        'parameters.exercise_placeholder': 'напр.: Бег, Йога, Спортзал',
        'parameters.anxiety': 'Тревожность',
        'parameters.anxiety_placeholder': 'напр.: Нет, Легкая, Средняя',
        'parameters.energy': 'Энергия',
        'parameters.energy_placeholder': 'напр.: Низкая, Нормальная, Высокая',
        'parameters.notes': 'Заметки',
        'parameters.notes_placeholder': 'Дополнительные заметки...',
        'parameters.save': 'Сохранить параметры',
        'parameters.load': 'Загрузить параметры',
        'parameters.insights': 'Аналитика',
        
        // Sidebar menu
        'menu.feed': '📱 Лента',
        'menu.profile': '👤 Профиль',
        'menu.circles': '👥 Круги',
        'menu.messages': '💬 Сообщения',
        'menu.parameters': '📊 Параметры',
        
        // Alerts
        'alerts.title': 'Оповещения',
        'alerts.no_alerts': 'Нет новых оповещений',
        
        // About page
        'about.title': 'О Тера Социал',
        'about.subtitle': 'Ваше безопасное пространство для здоровья, общения и личностного роста',
        'about.privacy_title': 'Конфиденциальность прежде всего',
        'about.privacy_desc': 'Ваш путь к здоровью приватен и безопасен. Делитесь только тем, что вам комфортно.',
        'about.track_title': 'Отслеживание прогресса',
        'about.track_desc': 'Отслеживайте свои параметры здоровья и наблюдайте свой рост с течением времени с аналитикой.',
        'about.community_title': 'Поддерживающее сообщество',
        'about.community_desc': 'Общайтесь с другими на похожих путях в среде без осуждения.',
        'about.communication_title': 'Безопасное общение',
        'about.communication_desc': 'Личные сообщения и круги позволяют контролировать, кто видит ваш контент.',
        'about.goals_title': 'Постановка целей',
        'about.goals_desc': 'Устанавливайте и отслеживайте личные цели с поддержкой и ответственностью сообщества.',
        'about.checkin_title': 'Ежедневные проверки',
        'about.checkin_desc': 'Регулярное отслеживание параметров помогает понять закономерности и триггеры.',
        
        // Support page
        'support.title': 'Центр поддержки',
        'support.subtitle': 'Мы здесь, чтобы помочь вам на пути к здоровью',
        'support.faq_title': 'Часто задаваемые вопросы',
        'support.faq1_q': 'Как отслеживать мои параметры здоровья?',
        'support.faq1_a': 'Перейдите на вкладку Параметры на вашей панели управления. Вы можете вводить ежедневные значения для настроения, сна, упражнений, тревожности и уровней энергии. Используйте календарь для сохранения и загрузки параметров для разных дат.',
        'support.faq2_q': 'Что такое Круги?',
        'support.faq2_a': 'Круги позволяют организовать ваши связи в группы: Общий, Близкие друзья и Семья. Вы можете контролировать, кто видит ваши посты на основе этих кругов.',
        'support.faq3_q': 'Как обновить мой профиль?',
        'support.faq3_a': 'Перейдите на вкладку Профиль, чтобы обновить вашу биографию, интересы, род занятий, цели и любимые хобби. Это помогает другим лучше понять вас.',
        'support.faq4_q': 'Мои данные конфиденциальны?',
        'support.faq4_a': 'Да! Мы серьезно относимся к конфиденциальности. Ваши данные о здоровье зашифрованы и видны только вам, если вы не решите ими поделиться.',
        'support.contact_title': 'Связаться с поддержкой',
        'support.subject': 'Тема',
        'support.message': 'Сообщение',
        'support.send': 'Отправить сообщение',
        
        // Calendar
        'calendar.prev': '←',
        'calendar.next': '→',
        'calendar.days': ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'],
        'calendar.months': ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'],
        
        // Messages
        'msg.success': 'Успех!',
        'msg.error': 'Ошибка',
        'msg.saved': 'Успешно сохранено!',
        'msg.loaded': 'Успешно загружено!',
        'msg.deleted': 'Успешно удалено!',
        'msg.sent': 'Сообщение отправлено!',
    }
};

// Current language state
let currentLanguage = 'en';

// Detect browser language on load
function detectBrowserLanguage() {
    const browserLang = navigator.language || navigator.userLanguage;
    const langCode = browserLang.split('-')[0]; // Get 'en' from 'en-US'
    
    // Check if we support this language
    if (translations[langCode]) {
        return langCode;
    }
    
    // Default to English if unsupported
    return 'en';
}

// Load saved language preference or detect
function initLanguage() {
    const savedLang = localStorage.getItem('userLanguage');
    
    if (savedLang && translations[savedLang]) {
        currentLanguage = savedLang;
    } else {
        currentLanguage = detectBrowserLanguage();
        localStorage.setItem('userLanguage', currentLanguage);
    }
    
    applyLanguage();
    applyRTL();
}

// Translate a single key
function t(key) {
    return translations[currentLanguage][key] || translations['en'][key] || key;
}

// Apply translations to all elements with data-i18n
function applyLanguage() {
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        const translation = t(key);
        
        // Handle different element types
        if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
            if (element.getAttribute('placeholder') !== null) {
                element.placeholder = translation;
            } else {
                element.value = translation;
            }
        } else {
            element.textContent = translation;
        }
    });
    
    // Update language selector if it exists
    const langSelector = document.getElementById('languageSelector');
    if (langSelector) {
        langSelector.value = currentLanguage;
    }
}

// Change language
function changeLanguage(lang) {
    if (translations[lang]) {
        currentLanguage = lang;
        localStorage.setItem('userLanguage', lang);
        applyLanguage();
        applyRTL();
        
        // Trigger custom event for dynamic content updates
        window.dispatchEvent(new CustomEvent('languageChanged', { detail: { language: lang } }));
    }
}

// Apply RTL for Hebrew and Arabic
function applyRTL() {
    const isRTL = currentLanguage === 'he' || currentLanguage === 'ar';
    document.documentElement.dir = isRTL ? 'rtl' : 'ltr';
    document.documentElement.lang = currentLanguage;
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLanguage);
} else {
    initLanguage();
}

// Export for use in other scripts
window.i18n = {
    t,
    changeLanguage,
    getCurrentLanguage: () => currentLanguage,
    getSupportedLanguages: () => Object.keys(translations)
};
