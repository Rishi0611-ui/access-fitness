pipeline {
    agent any
    environment {
        IMAGE = 'rishi0611ui/aceest-fitness'
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Install and Lint') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                    flake8 app.py test_app.py
                '''
            }
        }

stage('Test') {
            steps {
                sh '''
                    . venv/bin/activate
                    pytest -v
                '''
            }
        }
        stage('Docker Build') {
            steps {
                sh "docker build -t ${IMAGE}:v${BUILD_NUMBER} -t ${IMAGE}:latest ."
            }
        }

stage('Docker Push') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DH_USER', passwordVariable: 'DH_PASS')]) {
                    sh '''
                        echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin
                        docker push ${IMAGE}:v${BUILD_NUMBER}
                        docker push ${IMAGE}:latest
                    '''
                }
            }
        }

stage('Deploy Local') {
            steps {
                sh '''
                    docker rm -f aceest-jenkins || true
                    docker run -d -p 5001:5000 --name aceest-jenkins ${IMAGE}:latest
                    sleep 5
                    curl http://localhost:5001/health
                '''
            }
        }
    }
}
