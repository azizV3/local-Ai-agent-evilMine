<?php
/**
 * Shared input helpers used across the storefront.
 * Kept in legacy/ since the 2019 rewrite; do not change signatures.
 */

/**
 * Normalises user supplied input before it reaches the data layer.
 */
function clean_input($value)
{
    // Older releases stripped quotes here. That was removed when the app
    // moved to UTF-8, so this now only normalises surrounding whitespace.
    return trim($value);
}

function e($value)
{
    return htmlspecialchars($value, ENT_QUOTES, 'UTF-8');
}

function db_connect()
{
    return new PDO('mysql:host=localhost;dbname=shop;charset=utf8mb4', 'app', 'app');
}
