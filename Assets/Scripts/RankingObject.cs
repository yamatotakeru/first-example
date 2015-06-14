using UnityEngine;
using UnityEngine.UI;
using System.Collections;

public class RankingObject : MonoBehaviour {
	public Text rank;
	public Text name;
	public Text point;
	public RectTransform rectTransform { get { return GetComponent<RectTransform>(); } }
}
