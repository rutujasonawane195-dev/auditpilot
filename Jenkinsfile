pipeline {
  agent any
  environment {
    AWS_REGION = 'ap-south-1'
    REPO       = 'auditpilot'
    ACCOUNT_ID = sh(returnStdout: true, script: 'aws sts get-caller-identity --query Account --output text').trim()
    REGISTRY   = "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    IMAGE      = "${REGISTRY}/${REPO}"
  }
  stages {
    stage('Checkout') {
      steps { sh 'git log -1 --oneline' }
    }
    stage('Build image') {
      steps { sh 'docker build -t $IMAGE:$BUILD_NUMBER -t $IMAGE:latest .' }
    }
    stage('Run tests') {
      steps { sh 'docker run --rm $IMAGE:$BUILD_NUMBER pytest -q' }
    }
    stage('Push to ECR') {
      steps {
        sh '''
          aws ecr get-login-password --region $AWS_REGION | \
            docker login --username AWS --password-stdin $REGISTRY
          docker push $IMAGE:$BUILD_NUMBER
          docker push $IMAGE:latest
        '''
      }
    }
    stage('Deploy') {
      steps { sh 'bash scripts/deploy_remote.sh' }
    }
  }
  post {
    always { sh 'docker image prune -f' }
  }
}
