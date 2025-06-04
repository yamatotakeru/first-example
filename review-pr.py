import os
import requests
import json
import google.generativeai as genai

# 環境変数からSecretsを読み込む
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")
# ★ここを修正★: GITHUB_TOKEN の代わりに、設定したシークレット名を使う
MY_GITHUB_PAT = os.environ.get("GEMINI_ACCESS_TOKEN") # <-- この行を修正

TOKEN_LEN=1000

# Gemini APIの設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-1.5-pro')
# 利用可能なモデルをリストアップしてデバッグ出力
print("Listing available Gemini models...")
# for m in genai.list_models():
# 	# generateContent をサポートするモデルのみをフィルタリング
# 	if 'generateContent' in m.supported_generation_methods:
# 		print(f"  - Model: {m.name}, Description: {m.description}")
# 	print("Finished listing models.")

def get_pr_diff(repo_full_name, pr_number, github_token):
	"""GitHub APIからPRの差分を取得する"""
	headers = {
		"Authorization": f"token {github_token}",
		# ★ここを修正！★
		# 最初のPRメタデータ取得時には、JSON形式をリクエストする
		"Accept": "application/vnd.github.v3+json", 
	}
	# まずPRのメタデータを取得
	pr_url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}"
	print(f"Requesting PR metadata from: {pr_url}")
	response = requests.get(pr_url, headers=headers)
	
	print(f"PR metadata response status: {response.status_code}")
	# ★ここを修正！★ メタデータ応答はJSONなので、json.dumpsで整形して出力
	print(f"PR metadata response text (first 500 chars): {json.dumps(response.json(), indent=2)[:500]}") 
	
	response.raise_for_status()
	
	try:
		pr_data = response.json()
		diff_url = pr_data['diff_url']
	except json.JSONDecodeError as e:
		print(f"Error decoding JSON from PR metadata response: {e}")
		print(f"Response text was: {response.text}")
		raise
	
	print(f"Requesting diff from: {diff_url}")
	# ★ここを修正！★ diff_urlにアクセスする際は、再度diff形式をリクエストするAcceptヘッダーを使う
	diff_headers = {
		"Authorization": f"token {github_token}",
		"Accept": "application/vnd.github.v3.diff",
	}
	diff_response = requests.get(diff_url, headers=diff_headers)
	
	print(f"Diff response status: {diff_response.status_code}")
	print(f"Diff response text (first 500 chars): {diff_response.text[:500]}")
	
	diff_response.raise_for_status()
	return diff_response.text

def post_pr_comment(repo_full_name, pr_number, comment_body, github_token): # ★引数名も変更★
	"""GitHub APIを使ってPRにコメントを投稿する"""
	headers = {
		"Authorization": f"token {github_token}", # ★ここも修正★
		"Accept": "application/vnd.github.v3+json",
	}
	url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
	payload = {"body": comment_body}
	response = requests.post(url, headers=headers, data=json.dumps(payload))
	response.raise_for_status()
	print(f"Comment posted successfully to PR #{pr_number}")

def main():
	# コマンドライン引数からPR番号、ワークフロー実行ID、ジョブIDを取得
	import sys
	if len(sys.argv) < 4:
		print("Usage: python review_pr.py <pr_number> <run_id> <job_id>")
		exit(1)
	
	pr_number = sys.argv[1]
	failed_run_id = sys.argv[2]
	failed_job_id = sys.argv[3]

	repo_full_name = os.environ.get("GITHUB_REPOSITORY")

	if not repo_full_name:
		print("Error: GITHUB_REPOSITORY environment variable not found.")
		exit(1)

	print(f"Processing PR #{pr_number} for analyzing failed job {failed_job_id} in run {failed_run_id} in {repo_full_name}...")

	try:
		# ... (以下、元のロジックを維持) ...
		# 1. 失敗したジョブのログを取得
		full_log = get_job_log(repo_full_name, failed_run_id, failed_job_id, MY_GITHUB_PAT)
		print("Failed job log fetched.")

		# ... (ログの切り詰め、プロンプト作成、Gemini呼び出し、コメント投稿のロジックは同じ) ...

	except requests.exceptions.RequestException as e:
		print(f"GitHub API Error: {e}")
		exit(1)
	except genai.types.BlockedPromptException as e:
		print(f"Gemini API Error: Prompt was blocked - {e}")
		exit(1)
	except Exception as e:
		print(f"An unexpected error occurred: {e}")
		import traceback
		traceback.print_exc()
		exit(1)

if __name__ == "__main__":
	main()