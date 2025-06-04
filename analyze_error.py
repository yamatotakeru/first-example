import os
import requests
import json
import google.generativeai as genai
import time

# 環境変数からSecretsを読み込む
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")
MY_GITHUB_PAT = os.environ.get("GEMINI_ACCESS_TOKEN")

# Gemini APIの設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-1.5-flash') # 1.5-flashは高速でコスト効率が良いので推奨

# 最大トークン長（必要に応じて調整）
MAX_LOG_TOKEN_LEN = 8000 # Gemini 1.5 Flashは最大1Mトークンですが、無料枠とコストを考慮し、短く設定

def get_job_log(repo_full_name, run_id, job_id, github_token):
	"""GitHub APIから特定のジョブのログを取得する"""
	headers = {
		"Authorization": f"token {github_token}",
		"Accept": "application/vnd.github.v3+json",
	}
	# まずジョブのURLを取得
	job_url = f"https://api.github.com/repos/{repo_full_name}/actions/runs/{run_id}/jobs"
	response = requests.get(job_url, headers=headers)
	response.raise_for_status()
	
	jobs = response.json().get('jobs', [])
	log_url = None
	for job in jobs:
		if str(job['id']) == str(job_id):
			log_url = job['url'] + '/logs' # 個別ジョブのログURL
			break
	
	if not log_url:
		raise ValueError(f"Job with ID {job_id} not found in run {run_id}")

	# ログコンテンツをダウンロード
	log_response = requests.get(log_url, headers=headers)
	log_response.raise_for_status()
	
	# ログはテキスト形式なので、json.JSONDecodeErrorは発生しないはず
	return log_response.text

def post_pr_comment(repo_full_name, pr_number, comment_body, github_token):
	"""GitHub APIを使ってPRにコメントを投稿する"""
	headers = {
		"Authorization": f"token {github_token}",
		"Accept": "application/vnd.github.v3+json",
	}
	url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
	payload = {"body": comment_body}
	response = requests.post(url, headers=headers, data=json.dumps(payload))
	response.raise_for_status()
	print(f"Comment posted successfully to PR #{pr_number}")

def main():
	repo_full_name = os.environ.get("GITHUB_REPOSITORY")
	pr_number = os.environ.get("GITHUB_REF").split('/')[2] # PRがトリガーの場合
	
	# エラー分析ワークフローの実行からログIDとジョブIDを取得
	# GITHUB_RUN_ID: 現在のワークフロー実行のID
	# GITHUB_JOB_ID: 現在のジョブのID（ここではエラーになったジョブのIDを渡す想定だが、
	#                このワークフローはそれ自体がエラー分析用なので、
	#                トリガー元のワークフローのID/ジョブIDが必要になる）
	# このスクリプトは、外部からエラーになったワークフローのRUN_IDとJOB_IDを引数として受け取ることを想定
	# 例: python analyze_error.py <run_id> <job_id> <pr_number>
	
	# ここではGitHub Actionsのペイロードから直接run_idとjob_idを渡すことを想定し、
	# ワークフローYAMLでenvに設定するか、steps.runで引数として渡す
	failed_run_id = os.environ.get("FAILED_WORKFLOW_RUN_ID")
	failed_job_id = os.environ.get("FAILED_JOB_ID") # エラーになった特定のジョブのID

	if not repo_full_name or not pr_number or not failed_run_id or not failed_job_id:
		print("Error: Missing required environment variables or arguments.")
		# PRトリガーではないワークフローからの呼び出しの場合の考慮
		if not pr_number and os.environ.get("GITHUB_EVENT_NAME") == "workflow_run":
			 # workflow_runトリガーの場合、PR番号はevent.workflow_run.pull_requestsから取得
			 event_payload = json.loads(os.environ.get("GITHUB_EVENT_PATH"))
			 pull_requests = event_payload['event']['workflow_run']['pull_requests']
			 if pull_requests:
				 pr_number = pull_requests[0]['number']
			 else:
				 print("No associated PR found for workflow_run event.")
				 exit(0) # PRがない場合は処理をスキップ
		else:
			exit(1)

	print(f"Analyzing failed job {failed_job_id} in run {failed_run_id} for PR #{pr_number} in {repo_full_name}...")

	try:
		# 1. 失敗したジョブのログを取得
		full_log = get_job_log(repo_full_name, failed_run_id, failed_job_id, MY_GITHUB_PAT)
		print("Failed job log fetched.")

		# ログを短縮（トークン制限とコスト対策）
		if len(full_log) > MAX_LOG_TOKEN_LEN:
			truncated_log = full_log[-MAX_LOG_TOKEN_LEN:] # 後ろの方のエラーが多いので末尾を優先
			truncated_log = "\n... (log truncated due to length)\n" + truncated_log
			print("Log truncated.")
		else:
			truncated_log = full_log

		# 2. Geminiに分析を依頼するプロンプトを作成
		prompt = f"""
		You are an AI assistant specialized in analyzing GitHub Actions workflow logs.
		The following is a log from a failed GitHub Actions job.
		Please analyze the log, identify the most likely root cause of the failure, and suggest actionable steps to resolve it.
		Keep your response concise and formatted as a bulleted list.

		--- Failed Workflow Log ---
		{truncated_log}
		--- End of Log ---
		"""
		print("Sending log to Gemini for analysis...")
		response = model.generate_content(prompt)
		analysis_comment = response.text
		print("Analysis generated by Gemini.")

		# 3. 生成された分析コメントをPRに投稿
		comment_body = f"## 🤖 AI Workflow Failure Analysis for Job ID: {failed_job_id}\n\n{analysis_comment}\n\n---\n*This analysis was generated by Gemini AI.*"
		post_pr_comment(repo_full_name, pr_number, comment_body, MY_GITHUB_PAT)
		print("Analysis comment posted to PR.")

	except requests.exceptions.RequestException as e:
		print(f"GitHub API Error: {e}")
		exit(1)
	except genai.types.BlockedPromptException as e:
		print(f"Gemini API Error: Prompt was blocked - {e}")
		exit(1)
	except Exception as e:
		print(f"An unexpected error occurred: {e}")
		# 詳細なエラー情報をログに残す
		import traceback
		traceback.print_exc()
		exit(1)

if __name__ == "__main__":
	main()