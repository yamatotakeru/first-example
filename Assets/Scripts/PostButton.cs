using UnityEngine;
using System.Collections;

public class PostButton : MonoBehaviour {

	// Use this for initialization
	void Start () {
	
	}
	
	// Update is called once per frame
	void Update () {
	
	}

	void SendEvent() {
		BBBWWW www = new BBBWWW ();
		StartCoroutine(www.PostScores("name", 100));
	}
}
