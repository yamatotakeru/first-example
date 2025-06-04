import os
import requests
import json
import google.generativeai as genai
import time # 必要に応じてリトライ処理などで使用

# 環境変数からシークレットを読み込む
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")
MY_GITHUB_PAT = os.environ.get("GEMINI_ACCESS_TOKEN") # GitHub APIアクセス用

# Gemini APIの設定
genai.configure(api_key=GEMINI_API_KEY)
# 高速でコスト効率が良い Gemini 1.5 Flash を推奨
model = genai.GenerativeModel('models/gemini-1.5-flash') 

# Geminiに送るログの最大文字数（無料枠/コストを考慮して調整）
# Gemini 1.5 Flash は最大1Mトークンをサポートしますが、課金に注意
MAX_LOG_CHARS = 8000 

def get_job_log(repo_full_name, run_id, job_id, github_token):
	"""GitHub APIから特定のジョブのログを取得する"""
	headers = {
		"Authorization": f"token {github_token}",
		"Accept": "application/vnd.github.v3+json",
	}
	
	# まずワークフロー実行内のジョブリストを取得し、ログのURLを見つける
	jobs_url = f"https://api.github.com/repos/{repo_full_name}/actions/runs/{run_id}/jobs"
	jobs_response = requests.get(jobs_url, headers=headers)
	jobs_response.raise_for_status() # HTTPエラーがあれば例外を発生
	
	jobs_data = jobs_response.json().get('jobs', [])
	log_url = None
	for job in jobs_data:
		if str(job['id']) == str(job_id):
			# このAPIはログコンテンツへの一時的なリダイレクトURLを返す
			log_url = job['url'] + '/logs' 
			break
	
	if not log_url:
		raise ValueError(f"Job with ID {job_id} not found in run {run_id}")

	# ログコンテンツをダウンロード
	log_content_response = requests.get(log_url, headers=headers)
	log_content_response.raise_for_status()
	
	return log_content_response.text

def post_issue_comment(repo_full_name, issue_number, comment_body, github_token):
	"""特定のGitHub Issueにコメントを投稿する"""
	headers = {
		"Authorization": f"token {github_token}",
		"Accept": "application/vnd.github.v3+json",
	}
	url = f"https://api.github.com/repos/{repo_full_name}/issues/{issue_number}/comments"
	payload = {"body": comment_body}
	response = requests.post(url, headers=headers, data=json.dumps(payload))
	response.raise_for_status()
	print(f"Comment posted successfully to Issue #{issue_number}")

def create_issue(repo_full_name, issue_title, issue_body, github_token):
	"""新しいGitHub Issueを作成する"""
	headers = {
		"Authorization": f"token {github_token}",
		"Accept": "application/vnd.github.v3+json",
	}
	url = f"https://api.github.com/repos/{repo_full_name}/issues"
	payload = {"title": issue_title, "body": issue_body}
	response = requests.post(url, headers=headers, data=json.dumps(payload))
	response.raise_for_status()
	issue_data = response.json()
	print(f"New Issue created: {issue_data['html_url']}")
	return issue_data['number']

def main():
	repo_full_name = os.environ.get("GITHUB_REPOSITORY")
	
	# 失敗したワークフローの実行とジョブの詳細を環境変数から取得
	failed_workflow_name = os.environ.get("FAILED_WORKFLOW_NAME")
	failed_run_id = os.environ.get("FAILED_WORKFLOW_RUN_ID")
	failed_job_id = os.environ.get("FAILED_JOB_ID")
	failed_job_name = os.environ.get("FAILED_JOB_NAME")
	failed_run_url = os.environ.get("FAILED_WORKFLOW_RUN_URL")

	if not repo_full_name or not failed_run_id or not failed_job_id or not failed_workflow_name:
		print("エラー: 必要な環境変数 (REPO, RUN_ID, JOB_ID, WORKFLOW_NAME) が不足しています。")
		exit(1)

	print(f"ワークフロー '{failed_workflow_name}' のジョブ '{failed_job_name}' (ID: {failed_job_id}) の失敗を分析中 (実行ID: {failed_run_id})...")

	try:
		# 1. 失敗したジョブのログを取得
		full_log = get_job_log(repo_full_name, failed_run_id, failed_job_id, MY_GITHUB_PAT)
		print("失敗したジョブのログを取得しました。")

		# ログを短縮（トークン制限とコスト対策のため）
		if len(full_log) > MAX_LOG_CHARS:
			# エラーはログの最後に現れることが多いので、末尾から取得
			truncated_log = full_log[-MAX_LOG_CHARS:] 
			truncated_log = "\n... (ログは文字数制限のため切り詰められています)\n" + truncated_log
			print(f"ログを {MAX_LOG_CHARS} 文字に切り詰めました。")
		else:
			truncated_log = full_log
			print("ログは切り詰められませんでした（制限内です）。")


		# 2. Geminiに分析を依頼するプロンプトを作成
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

		# 3. 生成された分析コメントをGitHub Issueに投稿
		issue_title = f"🤖 ワークフロー失敗分析: '{failed_workflow_name}' / '{failed_job_name}' が実行 #{failed_run_id} で失敗"
		comment_body = f"## 🤖 AIワークフロー失敗分析\n\n" \
					   f"**ワークフロー:** {failed_workflow_name}\n" \
					   f"**ジョブ:** {failed_job_name}\n" \
					   f"**実行ID:** {failed_run_id}\n" \
					   f"**実行を見る:** [リンク]({failed_run_url})\n\n" \
					   f"---\n{analysis_comment}\n\n" \
					   f"---\n*この分析はGemini AIによって生成されました。*"
		
		# 分析結果を投稿するGitHub Issueの指定
		# オプションA: 既存の特定のIssueにコメントとして投稿する（推奨）
		# 事前に「ワークフロー失敗ログ」のような専用Issueを作成し、その番号をここに指定してください。
		TARGET_ISSUE_NUMBER = 1 # <--- ★ここに、分析結果をコメントしたい既存のIssue番号を指定してください★
		
		try:
			# ターゲットIssueが存在するか確認（任意だが良い習慣）
			requests.get(f"https://api.github.com/repos/{repo_full_name}/issues/{TARGET_ISSUE_NUMBER}", 
						 headers={"Authorization": f"token {MY_GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}).raise_for_status()
			# 存在すればコメントを投稿
			post_issue_comment(repo_full_name, TARGET_ISSUE_NUMBER, comment_body, MY_GITHUB_PAT)
			print(f"分析を既存のIssue #{TARGET_ISSUE_NUMBER} に投稿しました。")
		except requests.exceptions.HTTPError as e:
			if e.response.status_code == 404:
				# ターゲットIssueが見つからない場合、新しいIssueを作成してそこに投稿
				print(f"ターゲットIssue #{TARGET_ISSUE_NUMBER} が見つかりませんでした。新しいIssueを作成して分析を投稿します。")
				new_issue_number = create_issue(repo_full_name, issue_title, comment_body, MY_GITHUB_PAT)
				print(f"分析を新しいIssue #{new_issue_number} に投稿しました。")
			else:
				raise # その他のHTTPエラーは再発生させる
		
	except requests.exceptions.RequestException as e:
		print(f"GitHub APIエラー: {e}")
		exit(1)
	except genai.types.BlockedPromptException as e:
		print(f"Gemini APIエラー: プロンプトがブロックされました - {e}")
		exit(1)
	except Exception as e:
		print(f"予期せぬエラーが発生しました: {e}")
		import traceback
		traceback.print_exc() # エラートレースバックを出力
		exit(1)

if __name__ == "__main__":
	main()