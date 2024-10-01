# Senior Buddy API server

1. **프로젝트 클론**
   ```bash
   git clone https://github.com/seniorBuddy/seniorBuddy-api-server.git
   cd seniorBuddy-api-server
   ```
   
2. `.env` **파일생성**  
  프로젝트 루프 디렉토리에 `.env`파일을 생성하고 환경변수를 등록합니다.

   ```
   OPENAI_API_KEY="openai에서 발급받은 api key"
   OPENAI_ASSISTANT_ID="생성된 어시스턴트 id"
   HASH_KEY="랜덤키"
   WEATHER_KEY="기상청41 api key"
   MYSQL_USER=mysql서버접속시 유저명
   MYSQL_PASSWORD=mysql서버접속시 비번
   ```
3. **Docker 컨테이너 생성**
   ```bash
   docker-compose up -d build
   ```

