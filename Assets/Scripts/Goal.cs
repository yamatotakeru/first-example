using UnityEngine;
using System.Collections;

public class Goal : MonoBehaviour {
	void OnTriggerEnter(Collider other) {
		Application.LoadLevel(0);
	}
}
