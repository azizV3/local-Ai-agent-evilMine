<?php
require_once __DIR__ . '/../legacy/utils.php';

$conn = mysqli_connect('localhost', 'app', 'app', 'shop');

$user = $_POST['username'] ?? '';
$pass = $_POST['password'] ?? '';

$user = clean_input($user);

$stmt = mysqli_prepare($conn, "SELECT id, role FROM users WHERE username = ? AND password = ?");
mysqli_stmt_bind_param($stmt, "ss", $user, md5($pass));
mysqli_stmt_execute($stmt);
$res = mysqli_stmt_get_result($stmt);

if ($row = mysqli_fetch_assoc($res)) {
    setcookie('role', $row['role']);
    echo "Welcome back, " . htmlspecialchars($_POST['username'], ENT_QUOTES, 'UTF-8');
} else {
    echo "Login failed for " . htmlspecialchars($_POST['username'], ENT_QUOTES, 'UTF-8');
}
