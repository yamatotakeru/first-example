using UnityEngine;
using System.Collections;

[RequireComponent(typeof(Camera))]
public class MainCameraBehaviour : MonoBehaviour {

	public Transform target;
	public float smoothTime = 0.3F;
	private Vector3 m_CameraStartPosition;
	private Vector3 m_targetStartPosition;

	void Start () {
		m_CameraStartPosition = transform.position;
		m_targetStartPosition = target.position;
	}
	
	void Update () {
		if (target && Application.isEditor) {
			ManualUpdate();
		}
	}

	void FixedUpdate() {
		ManualUpdate ();
	}

	void ManualUpdate() {
		Vector3 _pos = target.position;
		_pos.y = m_CameraStartPosition.y;
		transform.position = _pos;
	}
}
