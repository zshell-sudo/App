from app import app

# For Vercel and other serverless platforms
# The app instance needs to be available at module level
application = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
