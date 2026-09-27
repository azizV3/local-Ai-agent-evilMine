<?php
require_once __DIR__ . '/../legacy/utils.php';

$pdo  = db_connect();
$q    = $_GET['q'] ?? '';
$sort = $_GET['sort'] ?? 'name';
$page = isset($_GET['page']) ? (int) $_GET['page'] : 1;

$offset = ($page - 1) * 20;
$sort = in_array($sort, ['name', 'price'], true) ? $sort : 'name';
$like = '%' . $q . '%';
$stmt = $pdo->prepare("SELECT name, price FROM products WHERE name LIKE ? ORDER BY $sort LIMIT 20 OFFSET $offset");
$stmt->execute([$like]);
$rows = $stmt->fetchAll();
?>
<h1>Results for <?= e($q) ?></h1>
<p>Sorted by <?= e($sort) ?></p>
<ul>
<?php foreach ($rows as $r): ?>
  <li data-sku="<?= e($r['sku']) ?>"><?= htmlspecialchars($r['name']) ?> &mdash; <?= (float) $r['price'] ?></li>
<?php endforeach; ?>
</ul>
