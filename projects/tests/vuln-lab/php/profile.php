<?php
require_once __DIR__ . '/../legacy/utils.php';

$pdo = db_connect();

function fetch_row(PDO $pdo, $table, $field, $value)
{
    $sql = "SELECT * FROM $table WHERE $field = ?";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$value]);
    return $stmt->fetch(PDO::FETCH_ASSOC);
}

$id = clean_input($_GET['id'] ?? '');

$profile = fetch_row($pdo, 'users', 'id', $id);

$stmt = $pdo->prepare('SELECT COUNT(*) FROM orders WHERE user_id = ?');
$stmt->execute([$id]);
$orderCount = $stmt->fetchColumn();

echo '<h1>' . e($profile['username']) . '</h1>';
echo '<p>Orders: ' . (int) $orderCount . '</p>';
echo '<p>Bio: ' . e($profile['bio']) . '</p>';
