# EKS Node Monitoring Tool

이 도구는 Amazon EKS 클러스터의 노드(EC2 인스턴스)를 모니터링하고 성능 메트릭을 수집하는 Python 애플리케이션입니다.

## 기능

- EKS 클러스터 노드 상태 모니터링
- EC2 인스턴스 메트릭 수집 (CPU, 메모리, 디스크 사용량)
- 노드 건강 상태 확인
- 임계값 기반 알림 생성
- CloudWatch 메트릭 수집
- 정기적인 모니터링 보고서 생성

## 요구사항

- Python 3.8 이상
- AWS 계정 및 적절한 권한
- EKS 클러스터에 대한 접근 권한
- 설치된 AWS CLI 및 구성된 자격 증명

## 설치

1. 저장소 클론:
```
git clone https://github.com/yourusername/eks-node-monitoring.git
cd eks-node-monitoring
```

2. 가상 환경 생성 및 활성화:
```
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 의존성 설치:
```
pip install -r requirements.txt
```

4. AWS 자격 증명 구성:
```
aws configure
```

## 구성

`config.py` 파일에서 다음 설정을 수정하세요:

- `AWS_REGION`: AWS 리전 (예: "us-west-2")
- `EKS_CLUSTER_NAME`: EKS 클러스터 이름
- `METRICS_INTERVAL`: 메트릭 수집 간격(초)
- `ALERT_THRESHOLD_CPU`: CPU 사용량 알림 임계값(%)
- `ALERT_THRESHOLD_MEMORY`: 메모리 사용량 알림 임계값(%)
- `ALERT_THRESHOLD_DISK`: 디스크 사용량 알림 임계값(%)
- `SNS_TOPIC_ARN`: (선택 사항) 알림을 보낼 SNS 토픽 ARN

## 사용 방법

모니터링 시작:

```
python eks_monitor.py
```

이 명령은 구성된 간격으로 모니터링 주기를 시작합니다. 각 주기마다 콘솔에 요약 정보가 출력되고 로그 파일에 자세한 정보가 기록됩니다.

## CloudWatch 에이전트 설정

메모리 및 디스크 사용량 메트릭을 수집하려면 EC2 인스턴스에 CloudWatch 에이전트를 설치해야 합니다. 이는 다음과 같이 수행할 수 있습니다:

1. EC2 인스턴스에 CloudWatch 에이전트 설치
2. 적절한 IAM 권한 구성
3. CloudWatch 에이전트 구성 파일 설정

자세한 내용은 [AWS CloudWatch 에이전트 설명서](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)를 참조하세요.

## 라이선스

MIT

## 기여

기여는 환영합니다! 이슈를 제출하거나 풀 리퀘스트를 보내주세요.