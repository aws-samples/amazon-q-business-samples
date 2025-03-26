# Using Existing S3 and Creating a New VPC 
use_existing_s3_bucket = true
existing_s3_bucket_name = "bank-united-demo"

vpc_option = "create_new"
vpc_cidr_block = "10.0.0.0/16"




# Creating a New S3 and Using Existing VPC
/* use_existing_s3_bucket = false
new_s3_bucket_name = "your-new-s3-bucket"

vpc_option = "use_existing"
existing_vpc_id = "vpc-xxxxxxxxxxxxx"



# Creating a New S3 and No VPC
/* use_existing_s3_bucket = false
new_s3_bucket_name = "your-new-s3-bucket"

vpc_option = "no_vpc"


# Using Existing S3 and No VPC
/* use_existing_s3_bucket = true
use_existing_s3_bucket = "your--s3-bucket"
vpc_option = "no_vpc"*/



#index type
index_type = "ENTERPRISE" 
/*index_type = "STARTER" */


#Advanced Image Indexing
enable_image_extraction = true

