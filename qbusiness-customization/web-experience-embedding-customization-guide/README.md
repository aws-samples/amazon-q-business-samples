# Amazon Q Business Web Experience Customization Guide with Embedding

## Overview
This guide provides step-by-step instructions for embedding the customized AmazonQ business Web experience.

## Pre-requisites
1. Please follow the steps [Amazon Q Business Web Experience Customization Guide](../web-experience-customization-guide/README.md) to customized the Web experience.
2. Python environment setup if python is not installed.

    ```
    # Install Python (3.7 or higher recommended) - https://www.python.org/downloads/
    python --version # Verify Python installation
    ```
## Create Sample Python Flask App to iframe the Web experience URL
1. Create Project Directory.
    ```
    # Create main project directory
    mkdir amazon-q-chat
    cd amazon-q-chat

    # Create virtual environment
    python -m venv venv

    # Activate virtual environment
    # On Windows:
    venv\Scripts\activate

    # On macOS/Linux:
    source venv/bin/activate
    ```

2. Create Project Structure.
    ```
    # Create required files
    touch app.py
    touch requirements.txt
    touch .env
    
    mkdir templates
    touch index.html
    ```
Project Structure will look like :-
amazon-q-chat/
├── venv/
├── templates/
│ └── index.html
├── app.py
├── requirements.txt
└── .env

3. Set up requirements.txt.
    ```
    Flask==2.3.3
    python-dotenv==1.0.0
    ```

4. Install Dependencies.
    ```
    pip install -r requirements.txt
    ```

5. Add below code to app.py.
    ```
    from flask import Flask, render_template
    from dotenv import load_dotenv
    import os
    
    # Load environment variables
    load_dotenv()
    
    app = Flask(__name__)
    
    # Get Amazon Q URL from env variables
    Q_BUSINESS_URL = os.getenv('AMAZON_Q_URL')
    
    @app.route('/')
    def home():
        return render_template('index.html', q_business_url=Q_BUSINESS_URL)
    
    if __name__ == '__main__':
        app.run(debug=True)
    ```

6. Add below code to templates/index.html.
    ```
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Amazon Q Chat</title>
        <style>
            body {
                margin: 0;
                padding: 20px;
                font-family: Arial, sans-serif;
            }
            .main-content {
                margin-right: 100px;
            }
            .chat-widget {
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 1000;
            }
            .chat-button {
                background-color: #FF9900;
                color: #232F3E;
                border: none;
                border-radius: 50%;
                width: 60px;
                height: 60px;
                cursor: pointer;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
            }
            .chat-container {
                position: fixed;
                bottom: 100px;
                right: 20px;
                width: 400px;
                height: 600px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 5px 20px rgba(0, 0, 0, 0.15);
                display: none;
                overflow: hidden;
            }
            .chat-container.active {
                display: block;
            }
            .chat-iframe {
                width: 100%;
                height: 100%;
                border: none;
            }
            .close-button {
                position: absolute;
                top: 10px;
                right: 10px;
                background: #232F3E;
                color: white;
                border: none;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
            }
            @media (max-width: 480px) {
                .chat-container {
                    width: 100%;
                    height: 100%;
                    bottom: 0;
                    right: 0;
                    border-radius: 0;
                }
            }
        </style>
    </head>
    <body>
        <div class="main-content">
            <h1>Welcome to Amazon Q Chat</h1>
            <p>Click the chat button to start a conversation.</p>
        </div>
        <div class="chat-widget">
            <button class="chat-button" onclick="toggleChat()">
            </button>
            <div class="chat-container" id="chatContainer">
                <button class="close-button" onclick="toggleChat()"> </button>
                <iframe
                    id="chatIframe"
                    src="{{ q_business_url }}"
                    class="chat-iframe"
                    allow="clipboard-write"
                    onload="handleIframeLoad()"
                ></iframe>
            </div>
        </div>
        <script>
            function toggleChat() {
                const container = document.getElementById('chatContainer');
                container.classList.toggle('active');
            }
            function handleIframeLoad() {
                const iframe = document.getElementById('chatIframe');
                const iframeDoc = iframe.contentWindow.document;

                try {
                    iframeDoc.body.appendChild(script);
                } catch (e) {
                    console.log('Failed to inject scroll handler:', e);
                }
            }
        </script>
    </body>
    </html>
    ```

7. Create .env file.
Replace <your-amazon-q-business-url> with your AmazonQ business Web experience URLs (For ex -
AMAZON_Q_URL=https://e4csgips.chat.qbusiness.us-east-1.on.aws/)

    ```
    FLASK_APP=app.py
    FLASK_ENV=development
    AMAZON_Q_URL=your-amazon-q-business-url
    ```

8. Run the app.
    ```
    flask run
    ```

![Flask App](/qbusiness-features/web-experience-embedding-customization-guide/images/flask_app.png)

Note the flask url in the terminal (for ex- http://127.0.0.1:5000/)

9. Amazon Q Embedding.
    1. Go to your Amazon Q business application
    2. Click on Amazon Q embedded
    3. Click Add allowed Website
    4. Enter the flask URL you copied from step 8 and click Add.

    ![Domain AllowList](/qbusiness-features/web-experience-embedding-customization-guide/images/domain_allowlist.png)

10. Test the Q App embedded.
    1. open the flask app url in browser.

    ![QChat App](/qbusiness-features/web-experience-embedding-customization-guide/images/qchat_app.png)

    2. Click chat icon on right bottom.
    3. If prompted for Sign in to use the Q Assistant . Click on Sign in.

    ![User SignIn](/qbusiness-features/web-experience-embedding-customization-guide/images/user_signin.png)

    4. After Sign In , try out the embedded Q app with sample prompt.

    ![QBusiness Embed App](/qbusiness-features/web-experience-embedding-customization-guide/images/qbusinessembed_app.png)

## License

This library is licensed under the MIT-0 License. See the [LICENSE](../LICENSE) file.