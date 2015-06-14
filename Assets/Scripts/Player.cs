using UnityEngine;
using System.Collections;

public class Player : MonoBehaviour {

	public const float ROTATE_SPEED = 15f;
	public const float MOVE_POWER = 5f;
	public const float MAX_ANGULAR_VELOCITY = 10; // The maximum velocity the ball can rotate at.

	public CNAbstractController MovementJoystick;
	public float movementSpeed = 5f;
	
	private Transform _mainCameraTransform;
	private Rigidbody _playerRigidbody;
	private Vector3 _startPoint;
	private bool _canControl;
	public bool canControl {
		set { _canControl = value; }
		get { return _canControl; }
	}

	public void PositionReset() {
		transform.position = _startPoint;
		_playerRigidbody.angularVelocity = Vector3.zero;
		_playerRigidbody.velocity = Vector3.zero;
	}

	// Use this for initialization
	void Start () {
		_canControl = true;
		_mainCameraTransform = Camera.main.GetComponent<Transform>();
		_playerRigidbody = GetComponent<Rigidbody> ();
		_playerRigidbody.maxAngularVelocity = MAX_ANGULAR_VELOCITY;
		_startPoint = transform.position;
	}

	// Update is called once per frame
	void Update () {
		if ( !_canControl ) return;
		Vector3 movement;

		#if UNITY_EDITOR
		movement = new Vector3(
			MovementJoystick.GetAxis("Horizontal"),
			0f,
			MovementJoystick.GetAxis("Vertical"));
		#endif
		if (Application.isMobilePlatform) {
			movement.x = Input.acceleration.x;
			movement.y = 0f;
			movement.z = Input.acceleration.y;
		} else {
		}

		CommonMovementMethod(movement);
	}

	private void MoveWithEvent(Vector3 inputMovement)
	{
		var movement = new Vector3(
			inputMovement.x,
			0f,
			inputMovement.y);
		
		CommonMovementMethod(movement);
	}
	/// <summary>
	/// Commons the movement method.
	/// </summary>
	/// <param name="movement">Movement.</param>
	private void CommonMovementMethod(Vector3 movement)
	{
		movement = movement;//_mainCameraTransform.TransformDirection(movement);
		movement.y = 0f;
		movement.Normalize();

		Vector3 _m = movement * MOVE_POWER;
		_playerRigidbody.AddTorque (new Vector3(_m.z, 0, -_m.x));
	}
}
