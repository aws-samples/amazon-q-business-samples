
# Enhancing Business Intelligence: Leveraging Amazon Bedrock LLMs for Custom Data Enrichment with Amazon Q to remove PII information

In today's data-driven business landscape, organizations seek innovative ways to extract meaningful insights from their vast data repositories. Amazon Q, combined with the powerful Large Language Models (LLMs) available through Amazon Bedrock, offers a transformative solution for custom data enrichment. This integrated approach enables businesses to automatically enhance their existing datasets with contextual information, identify hidden patterns, and generate actionable insights while maintaining data security and compliance. By leveraging these advanced AI capabilities, organizations can streamline their data analysis processes, improve decision-making accuracy, and unlock new opportunities for business growth.

In this case, we will showcase how PII information can be removed before ingesting the documents into Q Business using Custom Data Enrichment (CDE) using a Lambda function powered by LLM via Bedrock.

## Solution Architecture

Amazon Q Business incorporates a comprehensive data enrichment workflow that begins with raw data stored in S3 and processes it through Custom Data Enrichment (CDE) using Lambda functions powered by Amazon Bedrock's LLMs. The system follows a structured flow where data moves through a Data Source Connector, creating enriched content that is then indexed and made retrievable. This processed information becomes accessible to authenticated users through a web interface, where they can interact with the system using prompts. The entire process ensures that raw data is transformed into enriched, queryable information while maintaining security and user accessibility.

![Sol Arch](/code-samples/cde-PII-redaction/images/qbus_cde.png)

## Getting Started

### Prerequisites:
- Clone the Repository: To clone only the required Amazon Q Business CDE PII redaction project instead of the entire repository, follow the sparse checkout instructions in [sparse-checkout.md](/sparse-checkout.md).
- Create an identity center instance (IDC) in the region you would like to run this application on and add an user
- Make note of the IDC instance arn

### Steps:

1. Restore files for the dependencies Lambda layer using [install_layers.bat](/src/install_layers.bat)

2. Deploy CDK stack with the parameters

```
    cdk deploy --parameters idcInstanceArn="<your_idc_instance_arn>" --require-approval never
```

3. Deployed CDK stack deploys the below resources
    - Q Business application
    - Index
    - Retriever
    - Web experience
    - S3 buckets for data source and CDE
    - Uploads a sample pdf document to the data source S3 bucket
    - S3 Data Source
    - Cusom Data Enrichment (CDE) configuration
    - Lambda function with layers to apply logic to process data leveraging LLM via Bedrock
    - All IAM roles associated

4. Subscribe the user from the identity center to the Q Business application

5. Access web experience from the Q Business console

6. Execute the sample prompts

   You will notice the SSN and Date of Birth information are not found as they were removed from the raw data before getting indexed using the custom data enrichment lambda leveraging LLM via Bedrock.

   ![prompt1](/code-samples/cde-PII-redaction/images/sample_prompt1.png)
   ![prompt2](/code-samples/cde-PII-redaction/images/sample_prompt2.png)
   ![prompt3](/code-samples/cde-PII-redaction/images/sample_prompt3.png)
   ![prompt4](/code-samples/cde-PII-redaction/images/sample_prompt4.png)
   ![prompt5](/code-samples/cde-PII-redaction/images/sample_prompt5.png)
   ![prompt6](/code-samples/cde-PII-redaction/images/sample_prompt6.png)

## Clean up

- To delete the application either run the below command
```
    cdk destroy
```
- Or delete the stack from CloudFormation stacks page on AWS Console

## References

[Using Lambda functions for Amazon Q Business document enrichment](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/cde-lambda-operations.html)

## License:
This library is licensed under the MIT-0 License. See the [LICENSE](/LICENSE) file. 