# Save this as test_params.py and run it
from app import app
from flask import Response

test_html = '''
<!DOCTYPE html>
<html>
<head><title>Parameter Test</title></head>
<body>
<h1>Direct Test - Should Show 5 Parameters</h1>
<div id="test"></div>

<!-- Load the actual JavaScript file -->
<script src="/static/js/parameters-social.js"></script>

<!-- Test if it loaded -->
<script>
setTimeout(() => {
    const testDiv = document.getElementById('test');
    
    // Check if PARAMETER_CATEGORIES exists
    if (typeof PARAMETER_CATEGORIES !== 'undefined') {
        testDiv.innerHTML = '<h2>✅ JavaScript Loaded!</h2>';
        testDiv.innerHTML += '<p>Found ' + PARAMETER_CATEGORIES.length + ' categories:</p>';
        PARAMETER_CATEGORIES.forEach(cat => {
            testDiv.innerHTML += cat.emoji + ' ' + cat.id + '<br>';
        });
    } else {
        testDiv.innerHTML = '<h2>❌ PARAMETER_CATEGORIES not found</h2>';
    }
    
    // Check for old variables that shouldn't exist
    if (typeof mood !== 'undefined') {
        testDiv.innerHTML += '<p>⚠️ OLD variables still exist!</p>';
    }
}, 1000);
</script>
</body>
</html>
'''

# Add test route
with app.app_context():
    @app.route('/test-js-execution')
    def test_js():
        return Response(test_html, mimetype='text/html')
    
    print("Test route added!")
    print("Visit: https://socialsocial-72gn.onrender.com/test-js-execution")
