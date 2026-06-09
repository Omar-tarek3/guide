
## preequisites

- Create an AWS secret manager with name "terraformer-import-credentials" in your account. This is needed to store the IAM user access key as the code will read it from there.
You can execute this script with your access (if you have read access over the account) or you can create a new IAM user and assign this user SecretsManagerReadWrite, SignInLocalDevelopmentAccess and ReadOnlyAccess over the account.
- Based on step 2 (whether it is your access or if you create a new IAM user), create the access key id and access key for the user and stored it in two secrets "aws_access_key_id": "...", "aws_secret_access_key": "..." in the "terraformer-import-credentials"AWS secret manager which you have created in step 1
- Please open the attached zip file, inside which you will find a requirements.txt. This contains the required packages to be installed. please follow the steps and get the packages installed.
- Once you have installed the packages please open the python file from the zip "terraformer_only_import.py" and please go to line number 743-747, 755, 757, 762 and provide the respective inputs in there as mentioned in the comments.
- Then use aws cli (which you have installed as step 4) and use "awslogin" to first login as a user and then run the "terraformer_only_import.py" (Ensure all configurations are updated before that)
- Once the code runs successfully the output would be stored in the desired path as you would have updated in line number 762 as part of step5. Please share that out put file with us. 
- If you have a Lambda code, or other code binaries, we would request you share those separately as a zip with us or you can share in github repo as well.
- Please note: it might be easy if you have VS Code installed in your system you can directly perform all the required steps and run this from the VS code terminal.
 
