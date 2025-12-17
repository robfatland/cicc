# Cyberinfrastructure Cloud Clinic

Arrived at this state on 17-DEC-2025 which is "no critical info in this doc".


## Contents


1. Design and completion tracking
2. Questions + Task list
3. Script/Narrative for Cloud Clinic


## 1. Design and completion tracking


Objective: Build a "toy" processing pipeline that focuses on two classes
of service: AWS cloud services and Docker Container services. Rather than
engage AWS services using the browser console, we instead use two other
methods, both of which leverage the AWS API. 


- the `aws` command line interface
- the `boto3` Python library 


There are two S3 utility programs that mount object storage as a 
pseudo-filesystem.


- `s3fs` is an open source third party tool: Full POSIX behavior 
- `mount-s3` is an AWS-supported tool: Faster but not full POSIX


### Broad strokes narrative 


On localhost (laptop, desktop etcetera) we configure a "base of operations". 
This includes a localhost mount of an s3 bucket called `cicc-121325`. This is
mounted as `~/cicc/s3`.


On AWS create the corresponding s3 bucket. This will act as a globally-available 
data folder. We will populate this ten input data files.


We build a Docker Image and push that to DockerHub. 


We launch an EC2 instance, configure it, and save it as an AMI on AWS. 


We delete the EC2 VM (only the AMI remains) and from our localhost machine
we launch a new VM from the AMI. The sequence of events is: 


- AMI launches (c4.large) to produce a VM that...
    - ...boots 
    - ...runs a script that...
        - ...examines the S3 bucket to find a processing task
        - ...copies the data file to block storage
        - ...creates a semaphore in the S3 bucket
        - ...runs the DockerHub Image > Container which...
            - ...bind mounts the block storage 
            - ...runs a Python program `process.py`
            - ...returns SUCCESS and halts
        - ...copies back the result file
        - ...updates the tasklist.txt and completed.txt file
        - ...deletes the semaphore
    - ...terminates itself



### Building a c4.large EC2 VM AMI


```
# on the bash shell this command sequence...

# ...creates a keypair .pem file for accessing a VM using ssh
aws ec2 create-key-pair --key-name cicc --query 'KeyMaterial' --output text > ~/cicc/cicc.pem
chmod 400 ~/.keypairs/cicc.pem

# What follows gets down into the RBAC weeds on AWS. At a high level we have this sequence:
#     EC2 instance → Instance Profile → IAM Role → S3 Access Policy
#     Note the EC2 uses an intermediary (Instance Profile) to assume the IAM Role.

# And so the command sequence follows...

# ...create a trust policy file called trust-policy.json
cat > ~/cicc/trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

# ...using the above trust policy: Create a role that will grant s3 access 
#     Note: A trust policy defines what entity can use the associated role. 
#     In this case: EC2. This is a necessary but not sufficient condition.
#     We also need to make use of the Instance Profile.
aws iam create-role --role-name cicc-s3-role --assume-role-policy-document file://~/cicc/trust-policy.json

# ...attach an S3 full access policy to this role
aws iam attach-role-policy --role-name cicc-s3-role --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# ...create instance profile
#     Note: EC2 does not directly use a role. Rather it uses an instance profile that contains a role 
#     or roles. In this sense the instance profile is a bridging mechanism between the EC2 instance 
#     and the role. 
aws iam create-instance-profile --instance-profile-name cicc-s3-profile

# ...add the s3 access role to the instance profile
aws iam add-role-to-instance-profile --instance-profile-name cicc-s3-profile --role-name cicc-s3-role
```


At this point we are ready to create an EC2... but notice that the S3 access is global, not confined
to a single bucket. So let's do "cloud philosophy": We will delete everything and do it over again,
this time with access restricted to the project bucket `cicc-12132025`.



```
aws iam remove-role-from-instance-profile --instance-profile-name cicc-s3-profile --role-name cicc-s3-role
aws iam delete-instance-profile --instance-profile-name cicc-s3-profile
aws iam detach-role-policy --role-name cicc-s3-role --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam delete-role --role-name cicc-s3-role

cat > ~/cicc/s3-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "s3:*",
    "Resource": [
      "arn:aws:s3:::cicc-12132025",
      "arn:aws:s3:::cicc-12132025/*"
    ]
  }]
}
EOF

aws iam create-role --role-name cicc-s3-role --assume-role-policy-document file://~/cicc/trust-policy.json
aws iam put-role-policy --role-name cicc-s3-role --policy-name cicc-bucket-access --policy-document file://~/cicc/s3-policy.json
aws iam create-instance-profile --instance-profile-name cicc-s3-profile
aws iam add-role-to-instance-profile --instance-profile-name cicc-s3-profile --role-name cicc-s3-role
```


`aws iam create-role` and `aws iam create-instance-profile` both return JSON as 
confirmation. It is not necessary to save this information. In what follows we use identifiers 
that we have defined: role name `cicc-s3-role` and profile name `cicc-s3-profile`.
To reiterate the relationships: The EC2 instance assumes an Instance Profile that is
in turn a wrapper for the IAM Role; which is assigned the (now very specific) s3 policy.



At this point we can start an EC2 "c4.large" instance running Ubuntu. This is done using
an existing AWS-hosted "bare bones" Ubuntu AMI.


## Missing detail on EC2 CLI start


The CA had to go look up the AMI ID for the right Ubuntu image: 0efc etcetera. This
magic should be replaced with the actual lookup procedure.


```
aws ec2 run-instances \
  --image-id ami-0efcece6bed30fd98 \
  --instance-type c4.large \
  --key-name cicc \
  --iam-instance-profile Name=cicc-s3-profile \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=cicc-demo}]'


# re-get all of that instance metadata using this command...
aws ec2 describe-instances --filters "Name=tag:Name,Values=cicc-demo"

# recover the instance ip address using...
aws ec2 describe-instances --filters "Name=tag:Name,Values=cicc-demo" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text
```


Resulting ip address can be transcribed and typed in by hand; but a more rigorous approach
is to assign it to an environment variable called for example CICC_IP: 


```
echo "export CICC_IP=\$(aws ec2 describe-instances --filters \"Name=tag:Name,Values=cicc-demo\" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)" >> ~/.bashrc
source ~/.bashrc
printenv CICC_IP
```


### Part 2 of the EC2 process: Create an AMI


#### This is a side quest that needs doing


```
# update the package index
sudo apt update

# install docker 
sudo apt install -y docker.io

sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
newgrp docker
```


The EC2 task sequence: Simple version (no bind mount):


- EC2 starts up 
- Script runs
- Executes a Docker `run` from DockerHub



There are ten data files in the S3 bucket labeled in0.dat, in1.dat, 
in2.dat, ..., in9.dat. The idea is we want to process all 10 of 
them; but three processing tasks have already been completed. 
Here is the machinery in the s3 bucket: There is a file called 
tasklist.txt that lists files in3.dat through in9.dat (but not 
in0, in1, in2). This means that tasks 3 through 9 are still 
available. There are three output files out0.dat, out1.dat, 
out2.dat corresponding to complted tasks. So the objective is to 
have the running Container on the EC2 instance process in3.dat 
to produce out3.dat. This is after the Container has done a bind 
mount connecting the Container folder /data with the EC2 folder 
~/data. This means that the EC2 script is going to read the 
tasklist.txt file and it is going to go through some logical 
steps; and then it is going to set up the /data folder to contain






### Step-wise procedure




- Prepare the localhost environment
    - X Set up an account on AWS including Power User-type access to the console
        - LOH generate and download a new Access Key on the AWS console
            - DANGER: Keep the Access Key in a safe location
                - If it is compromised by a bad actor: Disaster ensues
                - Stolen access keys are used to mine bitcoin
                - Your loss will be measured in tens of thousands of dollars
                - The most common path to Access Key theft disaster:
                    - You commit an Access Key to a public GitHub repo
                    - You realize this mistake and Delete the Access Key
                    - A Bot finds the Access Key anyway: In your version history
                    - The Bot shuts down your account access
                    - The Bot starts mining bitcoin on dozens of AWS VMs
    - X Install VS Code and the Q Developer Coding Assistant Extension
        - Create an AWS Builder ID (free for individuals)
        - Can also use AWS IAM Identity Center
    - X Install the `aws` cli on localhost
        - This will be used to control workflow execution on the AWS cloud
    - X Instantiate credentials
        - `aws configure` with four fields
            - Access Key ID: A long string of characters
            - Secret Access Key: A longer string of characters (password-like)
            - AWS default region name e.g. `us-west-2` 
            - Default output format: One of `json`, `yaml`, `test`, `table`
        - These are stored in `~/.aws/credentials` and `~/.aws/config`
        - verify correct with `aws sts get-caller-identity`
    - X Install a Python environment (my case: `miniconda`)
    - X Create a dedicated conda environment `conda create -n cicc python=3.11`
    - Create a dedicated folder `cicc` containing this document
    - Create a test dataset as described below
        - 10 data files each 2MB 
        - random binary data 1.6e7 bits
        - filenames in0.dat, in1.dat, ..., in9.dat
        - create a 1000 byte kernel: random bits save as kernel.dat
        - Produce 3 output files out0.dat, out1.dat, out2.dat
            - Each output file is the corresponding input XOR the kernel
        - Produce a tasklist.txt file and a completed.txt file
    - Create an S3 bucket `cicc-121325`
        - Mount it on localhost as `~/cicc/s3`
    - Copy the data folder contents to `s3`
    - Set up a Docker Image on DockerHub
        - Start the Docker VM on localhost
        - Create a Dockerfile
            - Binds a datafile to an S3 bucket mounted on the host machine
            - Executes a Python script
- Configure the s3 bucket
    - `aws s3 mb s3://cicci-12132025`
    - `aws s3 ls` to confirm
- Mount the s3 bucket on localhost
    - `sudo apt get update`
    - `sudo apt get install s3fs`
    - `mkdir ~/cicc/s3`
    - `s3fs cicc-12132025 ~/cicc/s3 -o use_cache=/tmp -o uid=$(id -u) -o gid=$(id -g)`
        - optional: Alias this command in `.bash_aliases`
- Configure an AWS c4.large VM 
    - Launch Ubuntu c4.large VM
    - Run apt update / upgrade
    - Install docker
    - Create a run-on-boot script
        - See Section 3 below, Outline, on what this script does


### Another procedure needed


This document refers to cicc-12132025 and that's find but technically it 
should be removed in favor of a new bucket.


## 2. Questions + Task list


- Turn the `cicc` folder into a GiHub Repo
- Can the VM actions all be taken without rebooting the VM?
     - ...so the spectator does not have to keep reconnecting


## 3. Script/Narrative for Cloud Clinic


### Outline


- From localhost establish VS Code with Q Dev and Ubuntu terminal
- Verify `aws` cli
- Mount the AWS S3 bucket and inspect contents
    - Data files exist in0.dat etcetera
    - Three output files exist
    - tasklist.txt exists
    - completed.txt exists
- Start a lightweight AWS VM from an AMI
    - VM starts up in a couple of minutes (with established Keypair)
    - Recover the ip address; modify .config for VS Code Server ssh
    - Connect to this VM using VS Code Server: As an observer
    - The VM runs a startup script that does the following:
        - Log each action to a log.txt file in ~
        - Pause for five minutes (allows for spectator login, see above)
            - Log a remark every 60 seconds
        - Possibly: run `apt update` and `apt upgrade`?
        - Install docker?
        - Pull a predetermined docker image
        - Mount the S3 bucket as ~/s3
        - Open and read s3/tasklist.txt
        - Confirm that a tasklist datafile is present, no outfile exists yet
        - Write a semaphore file to prevent others from doing this task
        - Run the Docker Image as a Container passing the name of the data file
            - Docker Container reads the binary data file
            - Docker Container has a predetermined kernel 
            - Executes data XOR kernel 
            - Writes a data output file with the same identifier
            - Returns a SUCCESS value
        - Delete the semaphore
        - Modify s3/tasklist.txt
        - Modify s3/completed.txt
        - Verify the Container is halted
        - Terminate the VM (itself)
    - VS Code Server terminal no longer connected
    - Inspect S3 bucket for changes



### Script

- Welcome to Cloud Clinic episode 8: Automating a Container-based Workflow
- This presentation is entirely based on the Amazon Web Services cloud
    - Other clouds have completely parallel / equivalent services
- This presentation was prepared using the AWS Q Developer CA
    - Same comment applies: Other clouds have equivalent Coding Assistants
- The following steps were advance preparation
    - Configured localhost to connect to the AWS cloud
    - Created a lightweight cloud VM
    - Log on to the cloud VM using VS Code Server
    - Created a dedicated S3 object storage bucket
    - Populated the S3 bucket with a set of data files to process
    - Created tasks.csv and completed.csv files in the S3 bucket

