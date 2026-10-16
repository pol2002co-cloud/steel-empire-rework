# 배포 구성과 제작

전체 게임: 원본 게임의 .pak 데이터, Movie 영상, Mss 오디오 구성요소, 리워크 실행 파일·데이터 팩·런처·에디터·기본 화면 설정을 포함합니다. 별도 DOS 실행기나 개인 저장, 백업, 로그는 포함하지 않습니다.

Update: 지원 실행 파일 해시를 확인한 후 현재 누적 패치를 설치합니다. 기존 화면 설정과 모든 저장을 유지하며 프로그램 파일을 백업합니다.

Tools: 게임 폴더에 풀어 사용하는 런처 3종과 에디터입니다. 전체 게임에 이미 포함되어 있습니다.

Source: steel-rework의 패치 모듈·검증 코드·C# 런처 및 에디터 코드·제작용 데이터와 역사 실행 파일 스냅샷, 배포 스크립트를 포함합니다. 원본 게임 자체의 C/C++ 소스 코드는 포함되어 있지 않습니다.

제작에는 Python 3와 pefile, keystone-engine, capstone, unicorn이 필요합니다. archive.py의 SRC를 게임 설치 경로로 지정하세요. build.py는 검증된 원본 해시의 실행 파일이 설치 폴더나 ReworkBackups 안에 있어야 빌드합니다. 해당 원본은 전체 게임 ZIP의 development/SteelEmpire-original.exe로 제공됩니다. 이를 별도의 제작용 설치 사본의 ReworkBackups/original/SteelEmpire.exe로 복사할 수 있습니다.

C# 소스는 Windows .NET Framework csc.exe로 빌드합니다. 에디터는 char.dat를 리소스로 포함해야 합니다. 실제 게임 전체 분기 완주 검증은 별도입니다.

구버전 개별 설치 스크립트와 개인 저장 복구 스크립트는 공개 설치 프로그램으로 사용하지 않습니다. 최신 업데이트에는 경로를 지정할 수 있는 Install-Update.ps1을 사용하세요.
