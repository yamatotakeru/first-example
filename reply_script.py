# reply_script.py

import os
import requests
import json
import base64
import google.generativeai as genai

# --- 定数設定 ---
# コメントされた行の前後何行をコンテキストとしてAIに渡すか
CONTEXT_LINE_WINDOW = 5

# --- 環境変数の読み込み ---
# シークレット
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
# リポジトリとPRの情報
REPO_FULL_NAME = os.environ.get("GITHUB_REPOSITORY")
PR_NUMBER = os.environ.get("PR_NUMBER")
# コメントの情報
COMMENT_BODY = os.environ.get("COMMENT_BODY")
COMMENT_ID = os.environ.get("COMMENT_ID")
FILE_PATH = os.environ.get("FILE_PATH")
COMMIT_ID = os.environ.get("COMMIT_ID")
# コメントされた行 (1-based index)
# NOTE: lineは単一行、start_lineは複数行コメントの開始行
END_LINE = int(os.environ.get("END_LINE", 0))

# --- Gemini APIの初期設定 ---
try:
	genai.configure(api_key=GOOGLE_API_KEY)
	model = genai.GenerativeModel('models/gemini-1.5-flash')
except Exception as e:
	print(f"::error::Gemini APIの初期化に失敗しました: {e}")
	exit(1)

def get_code_context():
	"""コメントが付けられたファイルの、該当箇所周辺のコードを取得する"""
	headers = {
		"Authorization": f"token {GITHUB_TOKEN}",
		"Accept": "application/vnd.github.v3+json",
	}
	# ファイルの内容を取得するAPIエンドポイント
	url = f"https://api.github.com/repos/{REPO_FULL_NAME}/contents/{FILE_PATH}?ref={COMMIT_ID}"
	print(f"ファイル内容の取得: {url}")

	response = requests.get(url, headers=headers)
	response.raise_for_status()
	
	# レスポンスはBase64エンコードされているためデコードが必要
	file_content_b64 = response.json()['content']
	file_content = base64.b64decode(file_content_b64).decode('utf-8')
	
	lines = file_content.splitlines()
	
	# コメントされた行周辺のコードを切り出す (0-based indexに変換)
	start_index = max(0, END_LINE - 1 - CONTEXT_LINE_WINDOW)
	end_index = min(len(lines), END_LINE + CONTEXT_LINE_WINDOW)
	
	context_lines = lines[start_index:end_index]
	
	# 読みやすさのため、行番号を付けて整形する
	formatted_context = []
	for i, line in enumerate(context_lines, start=start_index + 1):
		prefix = ">>" if i == END_LINE else "  "
		formatted_context.append(f"{prefix} {i:4d}: {line}")
		
	return "\n".join(formatted_context)

def post_reply_to_comment(reply_body):
	"""特定のレビューコメントにリプライを投稿する"""
	headers = {
		"Authorization": f"token {GITHUB_TOKEN}",
		"Accept": "application/vnd.github.v3+json",
	}
	# コメントにリプライするためのAPIエンドポイント
	url = f"https://api.github.com/repos/{REPO_FULL_NAME}/pulls/{PR_NUMBER}/comments/{COMMENT_ID}/replies"
	payload = {"body": reply_body}
	
	print(f"リプライの投稿: {url}")
	response = requests.post(url, headers=headers, data=json.dumps(payload))
	response.raise_for_status()
	print("リプライの投稿に成功しました。")

def main():
	if not all([GOOGLE_API_KEY, GITHUB_TOKEN, REPO_FULL_NAME, PR_NUMBER, COMMENT_ID, COMMENT_BODY, FILE_PATH, COMMIT_ID, END_LINE > 0]):
		print("::error::必要な環境変数が不足しています。")
		return

	try:
		print("1. コメント周辺のコードを取得中...")
		code_context = get_code_context()
		
		print("\n--- 取得したコードコンテキスト ---")
		print(code_context)
		print("---------------------------\n")

		print("2. Geminiに返信内容の生成を依頼中...")
		
		prompt = f"""
		あなたはAIペアプログラミングアシスタントです。
		開発者がPull Requestのコードに以下のコメントを残しました。
		コメント内容と関連するコードを分析し、開発者への役立つ返信を生成してください。
		返信には、質問への回答、コードの改善案、あるいは別の視点からの提案などを含めることができます。
		回答は簡潔かつ建設的に、日本語で記述してください。

		---
		**ファイルパス:** `{FILE_PATH}`

		**関連コード:**
		```
		{code_context}
		```

		**開発者のコメント:**
		> {COMMENT_BODY}
		---

		**返信を作成してください:**
		"""

		response = model.generate_content(prompt)
		ai_reply = response.text
		
		print("\n--- 生成されたAIの返信 ---")
		print(ai_reply)
		print("------------------------\n")

		print("3. AIの返信をGitHubに投稿中...")
		
		# コメントのヘッダーを追加して投稿
		final_comment = f"🤖 **Gemini Assistantより**\n\n{ai_reply}"
		post_reply_to_comment(final_comment)
		
		print("処理が正常に完了しました。")

	except requests.exceptions.RequestException as e:
		print(f"::error::GitHub APIへのリクエストに失敗しました: {e}")
	except Exception as e:
		print(f"::error::予期せぬエラーが発生しました: {e}")
		import traceback
		traceback.print_exc()

if __name__ == "__main__":
	main()