pipeline {
    agent {
        docker {
            image 'python:3.11-slim'
            args '-u root'
        }
    }

    environment {
        AWS_REGION         = 'us-east-1'
        ECR_REGISTRY       = "${env.AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        IMAGE_NAME         = 'finrag'
        IMAGE_TAG          = "${env.GIT_COMMIT?.take(8) ?: 'latest'}"
        PYTHON_ENV         = 'ci'
    }

    options {
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {
        stage('Install') {
            steps {
                sh '''
                    pip install --no-cache-dir -e ".[dev]"
                '''
            }
        }

        stage('Lint') {
            parallel {
                stage('Ruff') {
                    steps {
                        sh 'ruff check app/ tests/'
                    }
                }
                stage('Black') {
                    steps {
                        sh 'black --check app/ tests/'
                    }
                }
                stage('Mypy') {
                    steps {
                        sh 'mypy app/'
                    }
                }
            }
        }

        stage('Security (SAST)') {
            steps {
                sh 'bandit -r app/ -ll -x app/tests'
            }
        }

        stage('Unit Tests') {
            environment {
                DATABASE_URL    = 'postgresql+asyncpg://test:test@localhost/test'
                SECRET_KEY      = 'ci-test-secret-key-minimum-32-chars-long'
                S3_BUCKET_NAME  = 'finrag-ci'
                OPENAI_API_KEY  = 'sk-test'
            }
            steps {
                sh '''
                    pytest tests/unit/ \
                        --cov=app \
                        --cov-report=xml:coverage.xml \
                        --cov-report=term-missing \
                        --cov-fail-under=85 \
                        -v
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results/**/*.xml'
                    publishCoverage adapters: [coberturaAdapter('coverage.xml')]
                }
            }
        }

        stage('Integration Tests') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                    changeRequest()
                }
            }
            environment {
                DATABASE_URL    = 'postgresql+asyncpg://test:test@localhost/test'
                SECRET_KEY      = 'ci-test-secret-key-minimum-32-chars-long'
                S3_BUCKET_NAME  = 'finrag-ci'
                OPENAI_API_KEY  = 'sk-test'
            }
            steps {
                sh '''
                    pytest tests/integration/ \
                        --cov=app \
                        --cov-report=xml:coverage-integration.xml \
                        -v
                '''
            }
        }

        stage('Docker Build') {
            when { branch 'main' }
            steps {
                script {
                    docker.build("${IMAGE_NAME}:${IMAGE_TAG}", "-f infra/docker/Dockerfile .")
                }
            }
        }

        stage('Push to ECR') {
            when { branch 'main' }
            steps {
                withAWS(region: "${AWS_REGION}", credentials: 'aws-ecr-credentials') {
                    sh '''
                        aws ecr get-login-password --region ${AWS_REGION} \
                            | docker login --username AWS --password-stdin ${ECR_REGISTRY}
                        docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${ECR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                        docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${ECR_REGISTRY}/${IMAGE_NAME}:latest
                        docker push ${ECR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                        docker push ${ECR_REGISTRY}/${IMAGE_NAME}:latest
                    '''
                }
            }
        }

        stage('Deploy to ECS') {
            when { branch 'main' }
            steps {
                withAWS(region: "${AWS_REGION}", credentials: 'aws-ecr-credentials') {
                    sh '''
                        aws ecs update-service \
                            --cluster finrag-cluster \
                            --service finrag-api \
                            --force-new-deployment \
                            --region ${AWS_REGION}
                        aws ecs wait services-stable \
                            --cluster finrag-cluster \
                            --services finrag-api \
                            --region ${AWS_REGION}
                    '''
                }
            }
        }
    }

    post {
        failure {
            echo "Pipeline failed on branch ${env.BRANCH_NAME} — commit ${env.GIT_COMMIT}"
        }
        success {
            echo "Pipeline succeeded — image ${IMAGE_NAME}:${IMAGE_TAG} deployed"
        }
        cleanup {
            cleanWs()
        }
    }
}
