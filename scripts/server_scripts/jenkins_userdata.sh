#!/bin/bash
# Jenkins CI/CD Automation Server Bootstrap Script
# Implements Slide 20 from AuditPilot Part 2
set -e

apt-get update
apt-get install -y fontconfig openjdk-21-jre docker.io unzip curl

# Install official Jenkins Debian-stable repository
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2026.key \
  -o /etc/apt/keyrings/jenkins-keyring.asc 2>/dev/null || \
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key \
  -o /etc/apt/keyrings/jenkins-keyring.asc

echo "deb [signed-by=/etc/apt/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" \
  > /etc/apt/sources.list.d/jenkins.list

apt-get update && apt-get install -y jenkins

# Install AWS CLI v2
curl -fsSL https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o /tmp/awscli.zip
unzip -q /tmp/awscli.zip -d /tmp && /tmp/aws/install
rm -rf /tmp/awscli.zip /tmp/aws

# Allow jenkins user to run docker
usermod -aG docker jenkins
systemctl enable --now docker
systemctl restart jenkins
