# Examples

## Accessing Secret from Jenkins with the vault jenkins plugin

```bash
#!/usr/bin/env groovy
def secrets = [
    [path: 'demo_secret_2', secretValues: [
        [envVar: 'testing', vaultKey: 'value_one'],
        [envVar: 'testing_again', vaultKey: 'value_two']]],
    [path: 'demo_secret', secretValues: [
        [vaultKey: 'test']]]
    ]

pipeline {
    agent any

    stages {
        stage('Test') {
            steps {
                withVault([vaultSecrets: secrets]) {
                    sh "curl -H 'Authorization: Bearer $testing' .... "
                    sh "curl -H 'Authorization: Bearer $testing_again' .... "
                    sh "curl -H 'Authorization: Bearer $test' .... "
                }
            }
        }
    }
}
```

## Accessing Secret from Jenkins with Puppet Certificates

```bash
export CERT_PATH="/etc/puppetlabs/puppet/ssl/certs/$HOSTNAME.pem"
export KEY_PATH="/etc/puppetlabs/puppet/ssl/private_keys/$HOSTNAME.pem"
export VAULT_ADDRESS="vault-nonprod01.corp.pdx02.clover.network"
export VAULT_NAMESPACE="jenkins"
export VAULT_CERT_ROLE="jenkins-slave-access"
export VAULT_AUTH_METHOD="puppet_tls"
LOGIN_RESP=$(curl --insecure --silent --request POST -H "X-Vault-Namespace:$VAULT_NAMESPACE" \
--cert $CERT_PATH --key $KEY_PATH  --data "{\"name\": \"$VAULT_CERT_ROLE\"}" \
https://$VAULT_ADDRESS:8200/v1/auth/$VAULT_AUTH_METHOD/login)
VAULT_TOKEN=$(echo $LOGIN_RESP | jq -r .auth.client_token)
DO_SOMETHING_RESPONSE=$(curl --insecure --silent --request GET -H "X-Vault-Namespace:$VAULT_NAMESPACE" -H "X-Vault-Token:$VAULT_TOKEN" https://$VAULT_ADDRESS:8200/v1/jenkins/demo_secret)
DO_SOMETHING_DATA=$(echo $DO_SOMETHING_RESPONSE | jq -r .data)
```

## Accessing Secrets with LDAP Credentials

```bash
VAULT_ADDRESS="vault-nonprod01.corp.pdx02.clover.network"
VAULT_NAMESPACE="techops"
VAULT_AUTH_METHOD="ldap"
LOGIN_RESP=$(curl --insecure --silent --request POST -H "X-Vault-Namespace:$VAULT_NAMESPACE" --data "{\"username\": \"$1\", \"password\": \"$2\"}" \
https://$VAULT_ADDRESS:8200/v1/auth/$VAULT_AUTH_METHOD/login/$1)
VAULT_TOKEN=$(echo $LOGIN_RESP | jq -r .auth.client_token)
SECRET_DATA=$(curl --insecure --silent --request GET -H "X-Vault-Namespace:$VAULT_NAMESPACE" -H "X-Vault-Token:$VAULT_TOKEN" https://$VAULT_ADDRESS:8200/v1/techops-admin/test_secret)
TEST_PASSWORD=$(echo $SECRET_DATA | jq -r .data.password)
echo $TEST_PASSWORD
```

## Uploading GCP Data to a Bucket retrieving a temporary GCP Access Token by LDAP Credentials

```bash
LDAP_PASSWORD=""
LDAP_USERNAME=""
GCP_FILE_NAME="test_file.txt"
GCP_BUCKET_NAME="dev-managed-gcp-bucket"
FILE_PATH="/tmp/$GCP_FILE_NAME"
VAULT_ADDRESS=“vault-nonprod01.corp.pdx02.clover.network”
VAULT_NAMESPACE=“gcp”
VAULT_GCP_ROLE_SET=“dev-managed-gcp-object-manager”
LOGIN_RESP=$(curl --insecure --request POST -H “X-Vault-Namespace:$VAULT_NAMESPACE” --data “{\“password\“: \“$LDAP_PASSWORD\“}” https://$VAULT_ADDRESS:8200/v1/auth/ldap/login/$LDAP_USERNAME)
VAULT_TOKEN=$(echo $LOGIN_RESP | jq -r .auth.client_token)
TOKEN_RESP=$(curl --insecure --request GET -H “X-Vault-Namespace:$VAULT_NAMESPACE” -H “X-Vault-Token:$VAULT_TOKEN” https://$VAULT_ADDRESS:8200/v1/google-cloud-access/token/$GCP_ROLE_SET)
GCP_ACCESS_TOKEN=$(echo $TOKEN_RESP| jq -r .data.token)
curl -X POST --data-binary "@$FILE_PATH" \
-H "Authorization: Bearer $GCP_ACCESS_TOKEN" \
-H "Content-Type: text/plain" \
"https://storage.googleapis.com/upload/storage/v1/b/$GCP_BUCKET_NAME/o?uploadType=media&name=$GCP_FILE_NAME"
```
