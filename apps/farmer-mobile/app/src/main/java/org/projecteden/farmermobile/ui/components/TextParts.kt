package org.projecteden.farmermobile.ui.components

/**
 * One half of a season window from the advice: "রোপণ: ~১ আগস্ট • কাটা: ~৩ নভেম্বর".windowPart(1) == "কাটা: ~৩ নভেম্বর".
 */
fun String.windowPart(index: Int): String = split(" • ").getOrNull(index)?.trim().orEmpty()
