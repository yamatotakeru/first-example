<?php
  $url = "";
  $user = "";
  $pass = "";
  $db_name = "";

  $link = mysql_connect($url,$user,$pass) or die("");
  $sdb = mysql_select_db($db_name,$link) or die("");
        $name = mysql_real_escape_string($_GET['name'], $link );
        $score = mysql_real_escape_string($_GET['score'], $link );
        $hash = $_GET['hash'];
		
        $secretKey="";
		
        $real_hash = md5($name . $score . $secretKey); 
        if($real_hash == $hash) {
            $query = "insert into scores values (NULL, '$name', '$score');";
            $result = mysql_query($query) or die('Query failed: ' . mysql_error());
        }
  mysql_close($link) or die("");
?>