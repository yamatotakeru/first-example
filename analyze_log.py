import os
import requests
import json
import google.generativeai as genai

# 環境変数から情報を読み込む
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") # ワークフローから自動的に付与される
REPO_FULL_NAME = os.environ.get("GITHUB_REPOSITORY")

# 失敗したワークフローとジョブの詳細
FAILED_WORKFLOW_NAME = os.environ.get("FAILED_WORKFLOW_NAME")
FAILED_RUN_ID = os.environ.get("FAILED_WORKFLOW_RUN_ID")
FAILED_JOB_ID = os.environ.get("FAILED_JOB_ID")
FAILED_JOB_NAME = os.environ.get("FAILED_JOB_NAME")
FAILED_RUN_URL = os.environ.get("FAILED_WORKFLOW_RUN_URL")

# ★ 関連するPull Requestの番号
PULL_REQUEST_NUMBER = os.environ.get("PULL_REQUEST_NUMBER")

# Gemini APIの設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-1.5-flash')

# ログの最大文字数
MAX_LOG_CHARS = 8000

def get_job_log(job_id):
	"""GitHub APIから特定のジョブのログを取得する"""
	headers = {
		"Authorization": f"token {GITHUB_TOKEN}",
		"Accept": "application/vnd.github.v3+json",
	}
	# ジョブログのダウンロードURLを取得 (リダイレクトされる)
	log_url = f"https://api.github.com/repos/{REPO_FULL_NAME}/actions/jobs/{job_id}/logs"
	
	log_content_response = requests.get(log_url, headers=headers, allow_redirects=True)
	log_content_response.raise_for_status()
	
	return log_content_response.text

def post_comment(target_number, comment_body):
	"""特定のGitHub PRまたはIssueにコメントを投稿する"""
	headers = {
		"Authorization": f"token {GITHUB_TOKEN}",
		"Accept": "application/vnd.github.v3+json",
	}
	# PRもIssueの一種なので、同じエンドポイントを使える
	url = f"https://api.github.com/repos/{REPO_FULL_NAME}/issues/{target_number}/comments"
	payload = {"body": comment_body}
	response = requests.post(url, headers=headers, data=json.dumps(payload))
	response.raise_for_status()
	print(f"Comment posted successfully to Issue/PR #{target_number}")

def create_issue(issue_title, issue_body):
	"""新しいGitHub Issueを作成する"""
	headers = {
		"Authorization": f"token {GITHUB_TOKEN}",
		"Accept": "application/vnd.github.v3+json",
	}
	url = f"https://api.github.com/repos/{REPO_FULL_NAME}/issues"
	payload = {"title": issue_title, "body": issue_body}
	response = requests.post(url, headers=headers, data=json.dumps(payload))
	response.raise_for_status()
	issue_data = response.json()
	print(f"New Issue created: {issue_data['html_url']}")
	return issue_data['number']

def main():
	if not all([REPO_FULL_NAME, FAILED_RUN_ID, FAILED_JOB_ID, FAILED_WORKFLOW_NAME, GITHUB_TOKEN, GEMINI_API_KEY]):
		print("エラー: 必要な環境変数が不足しています。")
		exit(1)

	print(f"ワークフロー '{FAILED_WORKFLOW_NAME}' のジョブ '{FAILED_JOB_NAME}' (ID: {FAILED_JOB_ID}) の失敗を分析中...")

	try:
		# 1. 失敗したジョブのログを取得
		full_log = get_job_log(FAILED_JOB_ID)
		print("失敗したジョブのログを取得しました。")

		# ログを短縮
		if len(full_log) > MAX_LOG_CHARS:
			truncated_log = full_log[-MAX_LOG_CHARS:]
			truncated_log = "\n... (ログは文字数制限のため切り詰められています)\n" + truncated_log
			print(f"ログを {MAX_LOG_CHARS} 文字に切り詰めました。")
		else:
			truncated_log = full_log

		# 2. Geminiに分析を依頼
		prompt = f"""
		あなたはGitHub Actionsのワークフローログを分析するAIアシスタントです。
		以下は失敗したGitHub Actionsジョブのログです。
		ログを分析し、失敗の最も可能性の高い根本原因を特定し、それを解決するための実行可能な手順を提案してください。
		回答は簡潔な箇条書き形式でまとめてください。

		--- 失敗したワークフロー情報 ---
		ワークフロー名: {FAILED_WORKFLOW_NAME}
		ジョブ名: {FAILED_JOB_NAME}
		実行URL: {FAILED_RUN_URL}
		
		--- 失敗ログ ---
		{truncated_log}
		--- ログの終わり ---
		"""
		print("ログをGeminiに分析のため送信中...")
		response = model.generate_content(prompt)
		analysis_result = response.text
		print("Geminiによる分析が生成されました。")

		# 3. 分析結果を整形して投稿
		comment_body = (
			f"## 🤖 AIによるワークフロー失敗分析\n\n"
			f"**ワークフロー:** `{FAILED_WORKFLOW_NAME}`\n"
			f"**失敗したジョブ:** `{FAILED_JOB_NAME}`\n"
			f"**詳細ログ:** [Link to Run]({FAILED_RUN_URL})\n\n"
			f"---\n\n"
			f"{analysis_result}\n\n"
			f"---\n\n"
			f"*このコメントは、GitHub ActionsとGemini AIによって自動的に生成・投稿されました。*"
		)

		if PULL_REQUEST_NUMBER:
			# ★ PR番号があれば、そのPRにコメント
			print(f"分析結果をPull Request #{PULL_REQUEST_NUMBER} に投稿します。")
			post_comment(PULL_REQUEST_NUMBER, comment_body)
		else:
			# ★ PR番号がなければ、フォールバックとしてIssueを作成/コメント
			print("この実行はPull Requestに関連付けられていません。Issueに投稿します。")
			issue_title = f"🤖 ワークフロー失敗分析: {FAILED_WORKFLOW_NAME} / {FAILED_JOB_NAME}"
			# ここでは新しいIssueを毎回作成するロジックにしています。
			# 特定のIssueに集約したい場合は、別途ロジックを追加してください。
			create_issue(issue_title, comment_body)

	except requests.exceptions.RequestException as e:
		print(f"GitHub APIエラー: {e.response.text if e.response else e}")
		exit(1)
	except Exception as e:
		print(f"予期せぬエラーが発生しました: {e}")
		import traceback
		traceback.print_exc()
		exit(1)

if __name__ == "__main__":
	main()