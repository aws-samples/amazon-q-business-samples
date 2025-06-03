# Amazon Q Business Web Experience Customization Guide

## Overview
This guide provides step-by-step instructions for customizing Amazon Q Business web experience with custom CSS, logos, and fonts.

## Steps

### 1. CREATE AN S3 BUCKET
1. Open the Amazon S3 console.
2. Click "Create bucket".
3. Enter a unique bucket name (ex - qbusinesscsscustomize).
4. Select the same region as your Amazon Q Business application.
5. Click "Create bucket".

### 2. CONFIGURE BUCKET POLICY FOR PRIVATE S3 BUCKET
1. Add the following bucket policy for giving Amazon Q Business access to your web experience artifacts.
    1. Select the newly created bucket, Click on Permission tab.
    2. In the bucket policy replace the your-web-experinece-s3-object-arn and your-web-experinece-s3-object-arn/* with the bucket arn which you created.
    3. Replace your-webexperience-domain-without-https:// with your Amazon Q business Web Experience url (eg., “e4csgips.chat.qbusiness.us-east-1.on.aws”).
        ```
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PolicyForAmazonQWebAccessForWebExperienceArtifacts",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "application.qbusiness.amazonaws.com"
                    },
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Resource": [
                        "your-web-experinece-s3-object-arn",
                        "your-web-experinece-s3-object-arn/*"
                    ],
                    "Condition":{
                        "StringLike":{
                            "aws:Referer":[
                                "your-webexperience-domain-without-https://"
                            ]
                        },
                        "Bool": {
                            "aws:SecureTransport": "true"
                        }
                    }
                }
            ]
        }
        ```

    4. Here is the how the sample Policy for the bucket “qbusinesscsscustomize” should look like :-

        ```
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PolicyForAmazonQWebAccessForWebExperienceArtifacts",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "application.qbusiness.amazonaws.com"
                    },
                    "Action": "s3:GetObject",
                    "Resource": [
                        "arn:aws:s3:::qbusinesscsscustomize",
                        "arn:aws:s3:::qbusinesscsscustomize/*"
                    ],
                    "Condition": {
                        "StringLike": {
                            "aws:Referer": "e4csgips.chat.qbusiness.us-east-1.on.aws"
                        },
                        "Bool": {
                            "aws:SecureTransport": "true"
                        }
                    }
                }
            ]
        }
        ```

2. Disabled the ACL for the newly created bucket if it is enabled.
    1. Go to bucket permission.
    2. Look for Object Ownership and click Edit.
    3. Select ACLx disabled option and click Save changes.

    ![Disable ACLs](/qbusiness-features/web-experience-customization-guide/images/disable-acls.png)

### 3. UPLOAD ASSETS 
1. Upload the following files to your S3 bucket:
    1. Logo file (image/svg+xml, image/x-icon, and image/png).
    2. Favicon (image/svg+xml, image/x-icon, and image/png).
    3. Font file (supported formats: font/ttf, font/otf, font/woff, and font/woff2.).   

### 4. CSS CONFIGURATION
1. Create a file named theme.css with the following content:
        
    Note : For this example I used the Amazon branding.
    ```
    :root {
        --black: #000000;
        --white: #FFFFFF;
        --foreground: #232F3E;
        --primary: #FF9900;
        --primary-foreground: #FFFFFF;
        --secondary: #232F3E;
        --secondary-foreground: #FFFFFF;
        --card: #FFFFFF;
        --card-foreground: #232F3E;
        --popover: #FFFFFF;
        --popover-foreground: #232F3E;
        --tooltip: #232F3E;
        --tooltip-foreground: #FFFFFF;
        --muted: #D5DBDB;
        --muted-foreground: #666666;
        --accent: #007EB9;
        --accent-foreground: #FFFFFF;
        --info: #007EB9;
        --info-foreground: #FFFFFF;
        --success: #008296;
        --success-foreground: #FFFFFF;
        --warning: #E47911;
        --warning-foreground: #FFFFFF;
        --error: #D13212;
        --error-foreground: #FFFFFF;
        --destructive: #D13212;
        --destructive-foreground: #FFFFFF;
        --border: rgba(0, 0, 0, 0.08);
        --input: #FFFFFF;
        --ring: #FF9900;
        --radius: 12px;
        --background: #FFFFFF;
        --qbusiness-webexperience-title-color: #232F3E;
        --qbusiness-webexperience-font-typeface: "Amazon Ember", sans-serif;
        --qbusiness-webexperience-chat-user-background-color: #FF9900;
        --qbusiness-webexperience-chat-user-text-color: #232F3E;
        --qbusiness-webexperience-chat-agent-background-color: #FFFFFF;
        --qbusiness-webexperience-chat-agent-text-color: #232F3E;
        --qbusiness-webexperience-chat-logo-visibility: visible;
        --qbusiness-webexperience-logo-url: "https://qbusinesscsscustomize.s3.us-east-1.amaz
        --qbusiness-webexperience-favicon-url: "https://qbusinesscsscustomize.s3.us-east-1.a
    }
    ```

    Note :- Update the qbusiness-webexperience-logo-url, and qbusiness-webexperience-favicon-url
            url with the right file from S3 bucket in the theme.css.

    For Example
    ```
        --qbusiness-webexperience-logo-url: "https://qbusinesscsscustomize.s3.us-east-1.amazon
         --qbusiness-webexperience-favicon-url: "https://qbusinesscsscustomize.s3.us-east-1.ama
    ```
            
    2. Upload the theme.css file to S3 bucket.

    ![Theme File](/qbusiness-features/web-experience-customization-guide/images/themefile.png)
    
    ### 5. CONFIGURE AMAZON Q BUSINESS
    1. Open Amazon Q Business console.
    2. Select your application.
    3. Go to "Customize web experience".
    4. Select "Theme".
    5. Choose "Custom theming".
    6. Enter the S3 URL of your CSS file (https://YOUR-BUCKET-NAME.s3.YOUR-REGION.amazonaws.com/theme.css).

    ![Custom Theming](/qbusiness-features/web-experience-customization-guide/images/custom-theming.png)

    7. Save changes.

    ### 6. TEST THE CHANGES
    1. View the Web Experience URL that has now the customized branding.

    ![Custom Branding](/qbusiness-features/web-experience-customization-guide/images/custom-branding.png)

## License

This library is licensed under the MIT-0 License. See the [LICENSE](../LICENSE) file.

