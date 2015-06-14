<?php
  $url = "";
  $user = "";
  $pass = "";
  $db_name = "";

  $link = mysql_connect($url,$user,$pass) or die("");
  $sdb = mysql_select_db($db_name,$link) or die("");

    $query = "SELECT * FROM `scores` ORDER by `score` DESC LIMIT 30";
    $result = mysql_query($query, $link) or die('Query failed: ' . mysql_error());
 
    $num_results = mysql_num_rows($result);  
 
    for($i = 0; $i < $num_results; $i++)
    {
         $row = mysql_fetch_array($result);
         echo $row['name'] . "," . $row['score'] . "\n";
    }
  mysql_close($link) or die("");
?>