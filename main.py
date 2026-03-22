import os
import anthropic
import tweepy
from datetime import datetime, timedelta, timezone
from tavily import TavilyClient

KST = timezone(timedelta(hours=9))
now = datetime.now(KST)

# 1. Tavily로 뉴스 URL 수집
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
search_results = tavily.search(
    query="주요 경제 뉴스 금융 시장",
    search_depth="advanced",
    max_results=5,
    include_answer=False,
)

urls = [r["url"] for r in search_results["results"]]
print(f"수집된 URL {len(urls)}개:\n" + "\n".join(urls))

# 2. Tavily extract로 원문 추출
extract_results = tavily.extract(urls=urls)

raw_content = "\n\n---\n\n".join([
    f"출처: {r['url']}\n\n{r['raw_content'][:2000]}"
    for r in extract_results["results"]
])

# 3. Claude가 원문 기반으로 요약 + 설명 + X 포스트 작성
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=600,
    messages=[{
        "role": "user",
        "content": f"""다음은 {now.strftime('%Y-%m-%d')} 주요 경제 뉴스 원문입니다.

{raw_content}

아래 형식으로 X(트위터) 포스트를 작성해주세요.

형식:
- 첫 줄: 날짜 ({now.strftime('%m/%d')}) + 한 줄 헤드라인
- 핵심 이슈 2~3개를 이모지와 함께 나열
- 각 이슈마다 일반인도 이해할 수 있는 1~2문장 설명 포함
- 마지막 줄: #경제뉴스 #금융
- 전체 200자 이내 (한글은 글자당 2자로 계산되므로 반드시 짧게)
- X 단일 포스트 (스레드 아님)

포스트 텍스트만 출력하세요."""
    }]
)

post_text = message.content[0].text.strip()
print(f"최종 포스트:\n{post_text}")

# 4. X에 포스팅
auth = tweepy.OAuth1UserHandler(
    os.environ["X_API_KEY"],
    os.environ["X_API_SECRET"],
    os.environ["X_ACCESS_TOKEN"],
    os.environ["X_ACCESS_SECRET"],
)
api = tweepy.API(auth)
api.update_status(post_text)
print("X 포스팅 완료!")
