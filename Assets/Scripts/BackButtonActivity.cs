using UnityEngine;
using UnityEngine.UI;
using System.Collections;

public class BackButtonActivity : MonoBehaviour {

	public static BackButtonActivity instance = null;

	public string messageTitle;
	public string messageDescription;

	void Awake() {
		if ( instance == null ) {
			instance = this;
			DontDestroyOnLoad(gameObject);
		} else {
			Destroy(gameObject);
		}
	}

	// Update is called once per frame
	void Update () {
#if UNITY_ANDROID
		if (Input.GetKeyDown(KeyCode.Escape)) {
			if ( Application.loadedLevel != 0 ) {
				Application.LoadLevel(0);
			} else {
				ButtonEvent();
			}
		}
#endif
	}

	public void ButtonEvent() {
		MobileNativeDialog dialog = new MobileNativeDialog(messageTitle, messageDescription);
		dialog.OnComplete += OnDialogClose;
	}

	private void OnDialogClose(MNDialogResult result) {
		switch(result) {
		case MNDialogResult.YES:
			Application.Quit();
			break;
		case MNDialogResult.NO:
			break;
		}
	}
}
