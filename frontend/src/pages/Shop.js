import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";
import { ShoppingCart, Plus, Minus, X, CreditCard, Check } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Shop() {
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState({});
  const [showCart, setShowCart] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchParams] = useSearchParams();

  useEffect(() => {
    axios.get(`${API}/products`).then(r => setProducts(r.data.products)).catch(() => toast.error("Failed to load products"));
  }, []);

  useEffect(() => {
    const sessionId = searchParams.get("session_id");
    if (sessionId) {
      axios.get(`${API}/checkout/status/${sessionId}`)
        .then(r => {
          if (r.data.payment_status === "paid") {
            toast.success("Payment successful! Your plushie is on its way!");
            setCart({});
          } else {
            toast.info("Payment status: " + r.data.payment_status);
          }
        })
        .catch(() => {});
    }
  }, [searchParams]);

  const addToCart = (id) => setCart(prev => ({ ...prev, [id]: (prev[id] || 0) + 1 }));
  const removeFromCart = (id) => setCart(prev => {
    const n = { ...prev };
    if (n[id] > 1) n[id]--;
    else delete n[id];
    return n;
  });

  const cartItems = Object.entries(cart).map(([id, qty]) => {
    const p = products.find(x => x.id === id);
    return p ? { ...p, qty } : null;
  }).filter(Boolean);

  const total = cartItems.reduce((s, i) => s + i.price * i.qty, 0);
  const cartCount = Object.values(cart).reduce((s, v) => s + v, 0);

  const checkout = async (productId) => {
    setLoading(true);
    const qty = cart[productId] || 1;
    try {
      const { data } = await axios.post(`${API}/checkout/session`, {
        product_id: productId,
        quantity: qty,
        origin_url: window.location.origin,
      });
      if (data.url) window.location.href = data.url;
    } catch (e) {
      toast.error("Checkout failed");
    }
    setLoading(false);
  };

  return (
    <div className="pt-20 pb-16 min-h-screen">
      <div className="stars-bg fixed inset-0 -z-10" />
      <div className="max-w-6xl mx-auto px-6 md:px-12">
        <div className="flex items-center justify-between mb-10">
          <div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter uppercase" style={{ fontFamily: 'Orbitron, sans-serif' }}>
              Plushie <span className="text-[#D946EF]">Shop</span>
            </h1>
            <p className="text-slate-500 text-sm mt-2">Exclusive Bullpug merchandise</p>
          </div>
          <button onClick={() => setShowCart(!showCart)} data-testid="cart-toggle"
            className="relative p-3 rounded-xl border border-white/10 hover:border-[#D946EF]/50 transition-colors">
            <ShoppingCart className="w-5 h-5" />
            {cartCount > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-[#D946EF] text-[10px] font-bold flex items-center justify-center">
                {cartCount}
              </span>
            )}
          </button>
        </div>

        {searchParams.get("session_id") && (
          <div className="glass-card rounded-2xl p-6 mb-8 border-[#00FFA3]/30 bg-[#00FFA3]/5 flex items-center gap-3">
            <Check className="w-6 h-6 text-[#00FFA3]" />
            <div>
              <p className="font-bold text-[#00FFA3]">Order Confirmed!</p>
              <p className="text-sm text-slate-400">Your Bullpug plushie is being shipped to the cosmos.</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {products.map(p => (
            <div key={p.id} className="glass-card rounded-2xl overflow-hidden group hover:-translate-y-1 transition-all duration-300" data-testid={`product-${p.id}`}>
              <div className="h-56 overflow-hidden relative">
                <img src={p.image_url} alt={p.name} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" />
                <div className="absolute inset-0 bg-gradient-to-t from-[#05050A] via-transparent to-transparent" />
                <Badge className="absolute top-3 right-3 bg-[#00FFA3]/90 text-black font-bold text-xs">${p.price}</Badge>
              </div>
              <div className="p-5 space-y-3">
                <h3 className="font-bold text-sm" style={{ fontFamily: 'Orbitron, sans-serif' }}>{p.name}</h3>
                <p className="text-xs text-slate-500 line-clamp-2">{p.description}</p>
                <div className="flex items-center gap-2">
                  {cart[p.id] ? (
                    <div className="flex items-center gap-2 flex-1">
                      <button onClick={() => removeFromCart(p.id)} data-testid={`remove-${p.id}`}
                        className="w-8 h-8 rounded-lg border border-white/10 flex items-center justify-center hover:border-red-500/50">
                        <Minus size={14} />
                      </button>
                      <span className="text-sm font-bold flex-1 text-center">{cart[p.id]}</span>
                      <button onClick={() => addToCart(p.id)} data-testid={`add-${p.id}`}
                        className="w-8 h-8 rounded-lg border border-white/10 flex items-center justify-center hover:border-[#00FFA3]/50">
                        <Plus size={14} />
                      </button>
                    </div>
                  ) : (
                    <Button onClick={() => addToCart(p.id)} data-testid={`add-cart-${p.id}`}
                      className="flex-1 bg-white/5 border border-white/10 text-white text-xs rounded-xl hover:bg-white/10">
                      <ShoppingCart className="w-3 h-3 mr-2" /> Add to Cart
                    </Button>
                  )}
                  <Button onClick={() => checkout(p.id)} disabled={loading} data-testid={`buy-${p.id}`}
                    className="bg-[#D946EF] text-white text-xs rounded-xl font-bold hover:scale-105 transition-transform">
                    <CreditCard className="w-3 h-3 mr-1" /> Buy
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {showCart && cartItems.length > 0 && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={() => setShowCart(false)}>
            <div className="glass-card rounded-2xl p-6 w-full max-w-md m-4 border border-white/10" onClick={e => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-lg" style={{ fontFamily: 'Orbitron, sans-serif' }}>Cart</h3>
                <button onClick={() => setShowCart(false)} data-testid="close-cart"><X size={20} /></button>
              </div>
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {cartItems.map(item => (
                  <div key={item.id} className="flex items-center justify-between p-3 rounded-lg border border-white/5">
                    <div className="flex items-center gap-3">
                      <img src={item.image_url} alt={item.name} className="w-10 h-10 rounded-lg object-cover" />
                      <div>
                        <p className="text-sm font-bold">{item.name}</p>
                        <p className="text-xs text-slate-500">{item.qty} x ${item.price}</p>
                      </div>
                    </div>
                    <p className="text-sm font-bold text-[#00FFA3]">${(item.price * item.qty).toFixed(2)}</p>
                  </div>
                ))}
              </div>
              <div className="mt-4 pt-4 border-t border-white/10 flex items-center justify-between">
                <p className="font-bold" style={{ fontFamily: 'Orbitron, sans-serif' }}>Total: ${total.toFixed(2)}</p>
                <Button onClick={() => cartItems[0] && checkout(cartItems[0].id)} disabled={loading}
                  data-testid="checkout-btn"
                  className="bg-[#D946EF] text-white font-bold rounded-xl hover:scale-105 transition-transform">
                  {loading ? "..." : "Checkout"}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
