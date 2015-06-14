using UnityEngine;
using UnityEngine.UI;
using System.Collections;
using System.Collections.Generic;

public class RankingController : MonoBehaviour
{
	public bool debugMode = false;
	private bool _showedRankList;
	public bool showed
	{
		set {
			_showedRankList = value;
			gameObject.SetActive(value);
			if ( value && !string.IsNullOrEmpty(rankingData) ) {
				StartCoroutine (GetScores ());
			}
		}
		get { return _showedRankList; }
	}
	private string rankingData;
	/// <summary>
	/// 本当はSimpleJSONなどを使用するのだが
	/// 今回はサンプルということもあって使用しない
	/// </summary>
	private class User
	{
		public int rank;
		public string name;
		public int highScore;
		public RankingObject viewObject;
	}
	private List<User> _users;

	public RankingObject rankingBaseObject;
	public ScrollRect rankingView;

	public void CloseEvent() {
		showed = false;
	}

	void Start ()
	{
		_showedRankList = false;
		rankingData = "";
		_users = new List<User> ();
		StartCoroutine (GetScores ());
	}
		
	// Get the scores from the MySQL DB to display in a GUIText.
	// remember to use StartCoroutine when calling this function!
	IEnumerator GetScores ()
	{
		WWW hs_get = new WWW (BBBWWW.highscoreURL);
		yield return hs_get;
		if (hs_get.error != null) {
			print ("There was an error getting the high score: " + hs_get.error);
		} else {
			Debug.Log(hs_get.text);
			rankingData = hs_get.text;
			string[] ranks = rankingData.Split('\n');
			int max = _users.Count;
			for (int i = 0; i < max; i++) {
				RectTransform.Destroy(_users[i].viewObject.gameObject);
			}
			_users.Clear();
			int _rank = 1;
			float _height = 0;
			foreach (string item in ranks) {
				if ( string.IsNullOrEmpty(item) ) break;
				string[] _d = item.Split(',');
				User _u = new User();
				_u.rank = _rank;
				_u.name = _d[0];
				_u.highScore = int.Parse(_d[1]);
				_u.viewObject = GameObject.Instantiate(rankingBaseObject);

				_u.viewObject.rank.text = "" + _rank;
				_u.viewObject.name.text = _d[0];
				_u.viewObject.point.text = _d[1];
				_u.viewObject.rectTransform.SetParent(rankingView.content.transform);
				_u.viewObject.rectTransform.localScale = new Vector3(1,1,1);

				_u.viewObject.rectTransform.offsetMax = new Vector2(0, _u.viewObject.rectTransform.offsetMax.y);
				_u.viewObject.rectTransform.offsetMin = new Vector2(0, _u.viewObject.rectTransform.offsetMin.y);
				_u.viewObject.rectTransform.anchoredPosition = new Vector2(_u.viewObject.rectTransform.anchoredPosition.x, - _u.viewObject.rectTransform.rect.height * (_rank - 1));
				_users.Add(_u);
				_rank++;
				_height += ((RectTransform)_u.viewObject.transform).rect.height;
			}
			rankingView.content.sizeDelta = new Vector2(rankingView.content.sizeDelta.x, _height);
		}
	}

	/*
	string _score = "";
	string _name = "";
	Vector2 _scrollPosition = new Vector2();
	Rect _scrollViewPort = new Rect(0, 0, Screen.width*0.8f, Screen.height*0.6f);
	void OnGUI () {
		if (_showedRankList) {
			if ( GUI.Button(new Rect(Screen.width*0.1f, Screen.width*0.1f, Screen.width*0.05f, Screen.width*0.05f), "×") ) {
				showed = false;
			}
			_scrollPosition = GUI.BeginScrollView(new Rect(Screen.width*0.1f, Screen.width*0.2f, Screen.width*0.8f, Screen.height*0.6f), _scrollPosition, _scrollViewPort);
			int max = _users.Count;
			float _h = Screen.height / 12;
			GUI.contentColor = Color.black;
			for (int i = 0; i < max; i++) {
				GUI.Label(new Rect(0, i * _h, 120, _h), _users[i].name);
				GUI.Label(new Rect(120 + 20, i * _h, 120, _h), _users[i].highScore.ToString());
			}

			if ( _scrollViewPort.height < max * _h) {
				_scrollViewPort.height = max * _h;
			}
			GUI.EndScrollView();
		} else {
			return;
		}
		if (debugMode) {
			_score = GUI.TextField (new Rect(Screen.width*0.8f, Screen.height*0.6f, Screen.width*0.2f, Screen.height*0.1f), _score);
			_name = GUI.TextField (new Rect(Screen.width*0.8f, Screen.height*0.7f, Screen.width*0.2f, Screen.height*0.1f), _name);
			if ( GUI.Button(new Rect(Screen.width*0.8f, Screen.height*0.8f, Screen.width*0.2f, Screen.height*0.1f), "Send Score") ) {
				BBBWWW www = new BBBWWW();
				StartCoroutine (www.PostScores(_name, int.Parse(_score)));
			}
		}
	}
	*/
}

