pipeline {
    agent any

    environment {
        AWS_REGION = 'ap-south-1'
        ECR_REPO = '864981730114.dkr.ecr.ap-south-1.amazonaws.com/gdta'
        ECS_CLUSTER = 'snsihub-cluster-dev'
        ECS_SERVICE = 'gdta-td-service'
        TASK_FAMILY = 'gdta-td'
        CONTAINER_NAME = 'gdta'
    }

    stages {
        stage('AWS ECR Login') {
            steps {
                script {
                    sh 'aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO'
                }
            }
        }

        stage('Build & Push Docker Image') {
            steps {
                script {
                    sh """
                    docker build -t ${ECR_REPO}:latest .
                    docker tag ${ECR_REPO}:latest ${ECR_REPO}:latest
                    docker push ${ECR_REPO}:latest
                    """
                }
            }
        }

        stage('Register New Task Definition with Latest Image') {
            steps {
                script {
                    sh "aws ecs describe-task-definition --task-definition $TASK_FAMILY --query 'taskDefinition' > task-def.json"

                    sh """
                    jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy) |
                        .containerDefinitions[0].image = "${ECR_REPO}:latest"' task-def.json > new-task-def.json
                    """

                    sh 'aws ecs register-task-definition --cli-input-json file://new-task-def.json'
                }
            }
        }

        stage('Update ECS Service with New Task Definition') {
            steps {
                script {
                    def TASK_REVISION = sh(script: "aws ecs describe-task-definition --task-definition $TASK_FAMILY --query 'taskDefinition.revision' --output text", returnStdout: true).trim()
                    echo "New Task Definition Revision: ${TASK_REVISION}"

                    sh """
                    aws ecs update-service --cluster ${ECS_CLUSTER} --service ${ECS_SERVICE} --task-definition ${TASK_FAMILY}:${TASK_REVISION} --force-new-deployment
                    """
                }
            }
        }
    }

    post {
        success {
            echo 'Backend deployment successful.'
            sh 'docker image prune -a -f'
            sh 'docker container prune -f'
        }
        failure {
            echo 'Backend deployment failed.'
            sh 'docker image prune -a -f'
        }
        always {
            sh 'docker system prune -f --volumes'
        }
    }
}
