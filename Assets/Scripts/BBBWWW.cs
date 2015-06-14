using UnityEngine;
using System.Collections;

public class BBBWWW {
	public const string secretKey = "";
	public const string addScoreURL = "";
	public const string highscoreURL = "";

	// remember to use StartCoroutine when calling this function!
	public IEnumerator PostScores (string name, int score)
	{
		//This connects to a server side php script that will add the name and score to a MySQL DB.
		// Supply it with a string representing the players name and the players score.
		string hash = Md5Sum (name + score + secretKey);
		
		string post_url = addScoreURL + "name=" + WWW.EscapeURL (name) + "&score=" + score + "&hash=" + hash;
		// Post the URL to the site and create a download object to get the result.
		WWW hs_post = new WWW (post_url);
		yield return hs_post; // Wait until the download is done
		
		if (hs_post.error == null) {
			Debug.Log ("Get Success");
		} else {
			Debug.Log ("There was an error posting the high score: " + hs_post.error);
		}
	}

	public static string Md5Sum(string strToEncrypt)
	{
		System.Text.UTF8Encoding ue = new System.Text.UTF8Encoding();
		byte[] bytes = ue.GetBytes(strToEncrypt);
		
		// encrypt bytes
		System.Security.Cryptography.MD5CryptoServiceProvider md5 = new System.Security.Cryptography.MD5CryptoServiceProvider();
		byte[] hashBytes = md5.ComputeHash(bytes);
		
		// Convert the encrypted bytes back to a string (base 16)
		string hashString = "";
		
		for (int i = 0; i < hashBytes.Length; i++)
		{
			hashString += System.Convert.ToString(hashBytes[i], 16).PadLeft(2, '0');
		}
		
		return hashString.PadLeft(32, '0');
	}
}
