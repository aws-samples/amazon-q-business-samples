# Sparse Checkout

This repository contains diverse set of code samples, knowledge articles, and guides. To improve efficiency, you can use sparse checkout to download only specific projects, directories, or files based on your needs, instead of cloning the entire repository.

## Checkout process (Git 2.25+)
```
# Clone the repository with no checkout
git clone --no-checkout <repository-url>
cd <repository-name>

# Set up sparse checkout
git sparse-checkout set path/to/desired/directory

# Checkout the content
git checkout main
```

##### Example with Amazon Q Business samples repository
```
# Clone the repository with no checkout
git clone --no-checkout git@github.com:aws-samples/amazon-q-business-samples.git
cd amazon-q-business-samples

# Set up sparse checkout
git sparse-checkout set code-samples/python/iam-federation-samples

# Checkout the content
git checkout main
```

## Checkout process (Git <2.25)

1. First, create an empty local repository:
    ```
    mkdir my-project
    cd my-project
    git init
    git remote add origin <repository-url>
    ```
1. Enable sparse checkout:
    ```
    git config core.sparseCheckout true
    ```
1. Specify which directories/files you want to check out by adding patterns to the sparse-checkout file:
    ```
    # For Unix-like systems
    echo "path/to/desired/directory/*" >> .git/info/sparse-checkout
    # For Windows
    echo path/to/desired/directory/* >> .git/info/sparse-checkout
    ```
1. Pull the content:
    ```
    git pull origin main
    ```
