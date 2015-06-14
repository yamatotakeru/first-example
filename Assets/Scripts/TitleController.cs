using UnityEngine;
using System.Collections;

public class TitleController : MonoBehaviour {
	public void GotoMiniGameScene() {
		Application.LoadLevel("level1");
	}
	public void GotoNotificationTestScene() {
		Application.LoadLevel("notification");
	}
}
