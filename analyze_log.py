# analyze_log.py

import os
import requests
import json
import google.generativeai as genai
import time
import sys # コマンドライン引数を読み込むため

# 環境変数からSecretsを読み込む
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")
MY_GITHUB_PAT = os.environ.get("GEMINI_ACCESS_TOKEN")

# Gemini APIの設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-1.5-flash') 

MAX_LOG_CHARS = 8000 

def get_job_log(repo_full_name, run_id, job_id, github_token):
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

def post_comment_to_github(repo_full_name, target_id, comment_body, github_token, is_pr=True): 
	headers = {
		"Authorization": f"token {github_token}",
		"Accept": "application/vnd.github.v3+json",
	}
	url = f"https://api.github.com/repos/{repo_full_name}/issues/{target_id}/comments"
	payload = {"body": comment_body}
	response = requests.post(url, headers=headers, data=json.dumps(payload))
	response.raise_for_status()
	if is_pr:
		print(f"コメントをPR #{target_id} に投稿しました。")
	else:
		print(f"コメントをIssue #{target_id} に投稿しました。")

def create_issue(repo_full_name, issue_title, issue_body, github_token):
	headers = {
		"Authorization": f"token {github_token}",
		"Accept": "application/vnd.github.v3+json",
	}
	url = f"https://api.github.com/repos/{repo_full_name}/issues"
	payload = {"title": issue_title, "body": issue_body}
	response = requests.post(url, headers=headers, data=json.dumps(payload))
	response.raise_for_status()
	issue_data = response.json()
	print(f"新しいIssueを作成しました: {issue_data['html_url']}")
	return issue_data['number']

def main():
	# ★ここを修正★: コマンドライン引数から情報を取得
	if len(sys.argv) < 7:
		print("使い方: python analyze_log.py <workflow_name> <run_id> <job_id> <job_name> <run_url> <pull_requests_json>")
		exit(1)

	# コマンドライン引数の取得
	failed_workflow_name = sys.argv[1]
	failed_run_id = sys.argv[2]
	failed_job_id = sys.argv[3]
	failed_job_name = sys.argv[4]
	failed_run_url = sys.argv[5]
	pull_requests_json_str = sys.argv[6] # JSON文字列として受け取る

	repo_full_name = os.environ.get("GITHUB_REPOSITORY")
	
	# PR番号の抽出
	pr_number = None
	if pull_requests_json_str and pull_requests_json_str != "null": # "null"文字列もチェック
		try:
			pull_requests = json.loads(pull_requests_json_str)
			if pull_requests and isinstance(pull_requests, list): # リストであることを確認
				pr_number = pull_requests[0].get('number')
				print(f"DEBUG: 関連するPR番号を検出: {pr_number}")
		except json.JSONDecodeError as e:
			print(f"DEBUG: pull_requests JSONのデコードに失敗しました: {e}")
			print(f"DEBUG: 受け取ったJSON文字列: {pull_requests_json_str[:200]}...") # デバッグ用
	
	if not repo_full_name:
		print("エラー: GITHUB_REPOSITORY 環境変数が設定されていません。")
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
		
		# PR番号があればPRにコメント、なければIssueにコメント
		if pr_number:
			post_comment_to_github(repo_full_name, pr_number, comment_body, MY_GITHUB_PAT, is_pr=True)
		else:
			TARGET_ISSUE_NUMBER = 1 # <--- ここに、全ての失敗分析結果をコメントしたい既存のIssue番号を指定してください
			
			try:
				requests.get(f"https://api.github.com/repos/{repo_full_name}/issues/{TARGET_ISSUE_NUMBER}", 
							 headers={"Authorization": f"token {MY_GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}).raise_for_status()
				post_comment_to_github(repo_full_name, TARGET_ISSUE_NUMBER, comment_body, MY_GITHUB_PAT, is_pr=False)
			except requests.exceptions.HTTPError as e:
				if e.response.status_code == 404:
					print(f"ターゲットIssue #{TARGET_ISSUE_NUMBER} が見つかりませんでした。新しいIssueを作成して分析を投稿します。")
					new_issue_number = create_issue(repo_full_name, issue_title, comment_body, MY_GITHUB_PAT)
					print(f"分析を新しいIssue #{new_issue_number} に投稿しました。")
				else:
					raise 

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