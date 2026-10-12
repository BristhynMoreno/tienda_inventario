(function () {
  "use strict";
  var root = document.getElementById("cart-root");
  if (!root) return;

  var KEY = "inv_carrito_v1_" + (root.dataset.user || "");
  var checkoutUrl = root.dataset.checkoutUrl;
  var csrf = root.dataset.csrf;
  var money = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 });

  var elList = document.getElementById("cart-items");
  var elTotal = document.getElementById("cart-total");
  var elCount = document.getElementById("cart-count");
  var elEmpty = document.getElementById("cart-empty");
  var elError = document.getElementById("cart-error");
  var elClient = document.getElementById("cart-cliente");
  var btnConfirm = document.getElementById("cart-confirm");
  var btnClear = document.getElementById("cart-clear");
  var elToast = document.getElementById("mini-toast");
  var fab = document.getElementById("cart-fab");
  var confirmHtml = btnConfirm.innerHTML;
  var toastTimer = null;

  var cart = load();
  render();

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; }
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(cart)); } catch (e) { /* sin almacenamiento */ }
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function toast(msg) {
    elToast.textContent = msg;
    elToast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { elToast.classList.remove("show"); }, 1800);
  }
  function bump() {
    fab.classList.remove("bump");
    void fab.offsetWidth;
    fab.classList.add("bump");
  }

  function render() {
    var ids = Object.keys(cart);
    var unidades = 0, total = 0;
    elList.innerHTML = ids.map(function (id) {
      var it = cart[id];
      unidades += it.cantidad;
      total += it.cantidad * it.precio;
      return '<li class="cart-line">' +
        '<div class="cl-info"><div class="cl-name" title="' + esc(it.nombre) + '">' + esc(it.nombre) + '</div>' +
        '<div class="cl-price">$ ' + money.format(it.precio) + ' c/u</div></div>' +
        '<div class="qty"><button type="button" data-cart-act="dec" data-id="' + id + '" aria-label="Quitar uno">−</button>' +
        '<span>' + it.cantidad + '</span>' +
        '<button type="button" data-cart-act="inc" data-id="' + id + '" aria-label="Agregar uno">+</button></div>' +
        '<div class="cl-sub">$ ' + money.format(it.cantidad * it.precio) + '</div>' +
        '<button type="button" class="cl-del" data-cart-act="del" data-id="' + id + '" aria-label="Eliminar"><i class="bi bi-trash"></i></button>' +
        '</li>';
    }).join("");
    elEmpty.hidden = ids.length > 0;
    elTotal.textContent = "$ " + money.format(total);
    elCount.textContent = unidades;
    elCount.hidden = unidades === 0;
    btnConfirm.disabled = ids.length === 0;
    btnClear.disabled = ids.length === 0;
  }

  function addItem(d) {
    var id = String(d.id);
    var stock = parseInt(d.stock, 10) || 0;
    var it = cart[id] || { id: id, cantidad: 0 };
    it.nombre = d.nombre;
    it.precio = parseFloat(d.precio) || 0;
    it.stock = stock;
    if (it.cantidad >= stock) { toast("Stock máximo disponible: " + stock); return; }
    it.cantidad += 1;
    cart[id] = it;
    save(); render(); bump();
    toast("Agregado: " + d.nombre);
  }

  function change(id, act) {
    var it = cart[id];
    if (!it) return;
    if (act === "inc") {
      if (it.cantidad >= it.stock) { toast("Stock máximo disponible: " + it.stock); return; }
      it.cantidad += 1;
    } else if (act === "dec") {
      it.cantidad -= 1;
      if (it.cantidad <= 0) delete cart[id];
    } else if (act === "del") {
      delete cart[id];
    }
    save(); render();
  }

  document.addEventListener("click", function (e) {
    var add = e.target.closest(".js-add");
    if (add) { addItem(add.dataset); return; }
    var act = e.target.closest("[data-cart-act]");
    if (act) change(act.dataset.id, act.dataset.cartAct);
  });

  btnClear.addEventListener("click", function () {
    cart = {}; save(); render();
    elError.hidden = true;
  });

  function fail(msg) {
    elError.textContent = msg;
    elError.hidden = false;
    btnConfirm.disabled = false;
    btnConfirm.innerHTML = confirmHtml;
  }

  btnConfirm.addEventListener("click", function () {
    var items = Object.keys(cart).map(function (id) {
      return { producto_id: Number(id), cantidad: cart[id].cantidad };
    });
    if (!items.length) return;
    elError.hidden = true;
    btnConfirm.disabled = true;
    btnConfirm.textContent = "Registrando…";

    fetch(checkoutUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
      body: JSON.stringify({ cliente: elClient.value, items: items })
    })
      .then(function (r) {
        return r.json().then(function (j) { return { ok: r.ok && j.ok, data: j }; });
      })
      .then(function (res) {
        if (res.ok) {
          cart = {}; save();
          window.location.href = res.data.url;
        } else {
          fail(res.data.error || "No se pudo registrar la venta.");
        }
      })
      .catch(function () {
        fail("No se pudo registrar la venta. Recarga la página e inténtalo de nuevo.");
      });
  });
})();
