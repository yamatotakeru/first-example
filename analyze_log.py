import os
import requests
import json
import google.generativeai as genai
import time

# 環境変数からSecretsを読み込む
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")
MY_GITHUB_PAT = os.environ.get("GEMINI_ACCESS_TOKEN") # GitHub APIアクセス用

# Gemini APIの設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-1.5-flash') 

MAX_LOG_CHARS = 8000 

def get_job_log(repo_full_name, run_id, job_id, github_token):
	"""GitHub APIから特定のジョブのログを取得する"""
	headers = {
		"Authorization": f"token {github_token}",
		"Accept": "application/vnd.github.v3+json",
	}
	
	jobs_url = f"https://api.github.com/repos/{repo_full_name}/actions/runs/{run_id}/jobs"
	jobs_response = requests.get(jobs_url, headers=headers)
	jobs_response.raise_for_status() 
	
	jobs_data = jobs_response.json().get('jobs', [])
	log_url = None
	for job in jobs_data:
		if str(job['id']) == str(job_id):
			log_url = job['url'] + '/logs' 
			break
	
	if not log_url:
		raise ValueError(f"Job with ID {job_id} not found in run {run_id}")

	log_content_response = requests.get(log_url, headers=headers)
	log_content_response.raise_for_status()
	
	return log_content_response.text

# ★ここを変更★ post_pr_comment 関数を再利用し、Issue関連の関数は削除または使用しない
def post_pr_comment(repo_full_name, pr_number, comment_body, github_token): 
	"""GitHub APIを使ってPRにコメントを投稿する"""
	headers = {
		"Authorization": f"token {github_token}",
		"Accept": "application/vnd.github.v3+json",
	}
	# PRへのコメントは、Issueのコメントと同じAPIエンドポイントを使用します
	url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
	payload = {"body": comment_body}
	response = requests.post(url, headers=headers, data=json.dumps(payload))
	response.raise_for_status()
	print(f"Comment posted successfully to PR #{pr_number}")


def main():
	repo_full_name = os.environ.get("GITHUB_REPOSITORY")
	
	failed_workflow_name = os.environ.get("FAILED_WORKFLOW_NAME")
	failed_run_id = os.environ.get("FAILED_WORKFLOW_RUN_ID")
	failed_job_id = os.environ.get("FAILED_JOB_ID")
	failed_job_name = os.environ.get("FAILED_JOB_NAME")
	failed_run_url = os.environ.get("FAILED_WORKFLOW_RUN_URL")
	
	# ★ここを追加★ 失敗したワークフロー実行に関連付けられたPRの情報を取得
	# workflow_run イベントのペイロードからPR番号を取得する
	# これはanalyze-failed-workflow.ymlの呼び出し元（event.workflow_run.pull_requests）から取得されることを想定
	pr_number = None
	event_payload_file = os.environ.get("GITHUB_EVENT_PAYLOAD_FILE")
	print(f"DEBUG: GITHUB_EVENT_PAYLOAD_FILE: {event_payload_file}")
	if event_payload_file and os.path.exists(event_payload_file):
		try:
			with open(event_payload_file, 'r', encoding='utf-8') as f:
				event_payload = json.load(f)
			print("DEBUG: GitHub event payload successfully loaded from file.")
			
			# workflow_run.pull_requests のパスは同じ
			workflow_run_data = event_payload.get('workflow_run', {})
			print(f"DEBUG: 'workflow_run' data type: {type(workflow_run_data)}")
			
			pull_requests = workflow_run_data.get('pull_requests', [])
			print(f"DEBUG: 'pull_requests' data: {pull_requests}")
			print(f"DEBUG: 'pull_requests' list length: {len(pull_requests)}")
	
			if pull_requests:
				pr_number = pull_requests[0].get('number')
				print(f"DEBUG: Found PR number: {pr_number}")
			else:
				print("DEBUG: 'pull_requests' list is empty or 'number' not found in first item.")
	
		except json.JSONDecodeError as e:
			print(f"DEBUG: Could not decode JSON from file '{event_payload_file}': {e}")
		except FileNotFoundError:
			print(f"DEBUG: File not found: '{event_payload_file}'")
	else:
		print("DEBUG: GITHUB_EVENT_PAYLOAD_FILE environment variable is empty or file does not exist.")
	
	# event_payload_str = os.environ.get("GITHUB_EVENT_PAYLOAD") # GITHUB_EVENT_PATH の内容
	# if event_payload_str:
	# 	try:
	# 		event_payload = json.loads(event_payload_str)
	# 		pull_requests = event_payload.get('workflow_run', {}).get('pull_requests', [])
	# 		if pull_requests:
	# 			pr_number = pull_requests[0].get('number') # 最初のPR番号を取得
	# 			print(f"Detected associated PR number: {pr_number}")
	# 	except json.JSONDecodeError:
	# 		print("Could not decode GITHUB_EVENT_PAYLOAD.")
			
	if not pr_number:
		print("エラー: 関連するPR番号が見つかりませんでした。PRにコメントできません。")
		exit(0) # PRに紐付かない場合は処理をスキップして成功終了

	if not repo_full_name or not failed_run_id or not failed_job_id or not failed_workflow_name:
		print("エラー: 必要な環境変数 (REPO, RUN_ID, JOB_ID, WORKFLOW_NAME) が不足しています。")
		exit(1)

	print(f"ワークフロー '{failed_workflow_name}' のジョブ '{failed_job_name}' (ID: {failed_job_id}) の失敗を分析中 (実行ID: {failed_run_id})...")

	try:
		full_log = get_job_log(repo_full_name, failed_run_id, failed_job_id, MY_GITHUB_PAT)
		print("失敗したジョブのログを取得しました。")

		if len(full_log) > MAX_LOG_CHARS:
			truncated_log = full_log[-MAX_LOG_CHARS:] 
			truncated_log = "\n... (ログは文字数制限のため切り詰められています)\n" + truncated_log
			print(f"ログを {MAX_LOG_CHARS} 文字に切り詰めました。")
		else:
			truncated_log = full_log
			print("ログは切り詰められませんでした（制限内です）。")

		prompt = f"""
		あなたはGitHub Actionsのワークフローログを分析するAIアシスタントです。
		以下は失敗したGitHub Actionsジョブのログです。
		ログを分析し、失敗の最も可能性の高い根本原因を特定し、それを解決するための実行可能な手順を提案してください。
		回答は簡潔な箇条書き形式でまとめてください。

		--- 失敗したワークフロー名: {failed_workflow_name} ---
		--- 失敗したジョブ名: {failed_job_name} ---
		--- 失敗したワークフロー実行URL: {failed_run_url} ---
		--- 失敗したワークフローログ ---
		{truncated_log}
		--- ログの終わり ---
		"""
		print("ログをGeminiに分析のため送信中...")
		response = model.generate_content(prompt)
		analysis_comment = response.text
		print("Geminiによる分析が生成されました。")

		comment_body = f"## 🤖 AIワークフロー失敗分析\n\n" \
					   f"**ワークフロー:** {failed_workflow_name}\n" \
					   f"**ジョブ:** {failed_job_name}\n" \
					   f"**実行ID:** {failed_run_id}\n" \
					   f"**実行を見る:** [リンク]({failed_run_url})\n\n" \
					   f"---\n{analysis_comment}\n\n" \
					   f"---\n*この分析はGemini AIによって生成されました。*"
		
		# ★ここを変更★ 取得したPR番号に対してコメントを投稿
		post_pr_comment(repo_full_name, pr_number, comment_body, MY_GITHUB_PAT)
		print(f"分析をPR #{pr_number} に投稿しました。")
		
	except requests.exceptions.RequestException as e:
		print(f"GitHub APIエラー: {e}")
		exit(1)
	except genai.types.BlockedPromptException as e:
		print(f"Gemini APIエラー: プロンプトがブロックされました - {e}")
		exit(1)
	except Exception as e:
		print(f"予期せぬエラーが発生しました: {e}")
		import traceback
		traceback.print_exc()
		exit(1)

if __name__ == "__main__":
	main()