import argparse 

from dotenv import dotenv_values
from typing import Dict
import boto3

config = dotenv_values('.env')
cognito_idp = boto3.client('cognito-idp')
cognito_identity = boto3.client('cognito-identity')
region = config.get('REGION')
bucket = config.get('BUCKET')
app_name= 'my-app'


class User:
    def __init__(self, username: str, password:str) -> None:
        self.username = username
        self.password = password

    def login(self) -> Dict:
        """authenticates user against a userpool

        Returns:
            Dict: returns a dictionary with id, access and refresh token
        """
        params = dict(AuthFlow='USER_PASSWORD_AUTH',
                      AuthParameters={
                          'USERNAME': self.username,
                          'PASSWORD': self.password
                      },
                      ClientId=config.get('CLIENT_ID'))
        return cognito_idp.initiate_auth(**params).get('AuthenticationResult')

    def get_identity(self, id_token: str) -> str:
        """Creates a new or returns an existing ideinity id from cognito identity pool

        Args:
            id_token (str): active id token from cognito pool

        Returns:
            str: identity id
        """
        params = dict(AccountId=config.get('ACCOUNT_ID'),
                      IdentityPoolId=f"{config.get('IDENTITY_POOL_ID')}",
                      Logins={
                          f"cognito-idp.{region}.amazonaws.com/{config.get('USER_POOL_ID')}": id_token
        })
        return cognito_identity.get_id(**params).get('IdentityId')

    def get_credentials(self) -> Dict:
        """Get STS credentials
        Returns:
            Dict: dict containig access_key_id, secret_access_key & session_token
        """
        tokens = self.login()
        id_token = tokens.get('IdToken')
        identity_id = self.get_identity(id_token)
        params = dict(IdentityId=identity_id,
                      Logins={
                          f"cognito-idp.{region}.amazonaws.com/{config.get('USER_POOL_ID')}": id_token
                      })
        return cognito_identity.get_credentials_for_identity(**params).get('Credentials'), identity_id


def main(username: str, password: str)-> None:
    """main method of the application
    Args:
        username (str): username/email id of user used for sign up in cognito pool
        password (str): password of the user
    """

    session_credentials, identity_id = User(username, password).get_credentials()
    session = boto3.Session(
        aws_access_key_id=session_credentials.get('AccessKeyId'),
        aws_secret_access_key=session_credentials.get('SecretKey'),
        aws_session_token=session_credentials.get('SessionToken'))

    s3 = session.resource('s3')
    s3.meta.client.upload_file(Filename = 'data.txt', Bucket = bucket, Key = f'{app_name}/{identity_id}/data.txt')
    print(f"You have uploaded a file to the S3 bucket. File location: s3://{bucket}/{app_name}/{identity_id}/data.txt")
    


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(dest='username', type=str, help="Username or email address")
    parser.add_argument(dest='password',type=str,  help="User password")
    args = parser.parse_args() 
    main(args.username, args.password)
