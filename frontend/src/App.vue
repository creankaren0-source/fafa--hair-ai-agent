<template>
  <div>
    <header class="welcome" :class="top ? 'expanded' : 'collapsed'">
      <div class="welcome-bg"></div>
      <div class="welcome-inner">
        <div class="welcome-expanded-content">
          <div class="avatar">🧚</div>
          <div class="grow">
            <div class="welcome-title">Hey~我是发发</div>
            <div class="welcome-sub">你的口袋的发型设计助手</div>
          </div>
          <button class="menu-btn" @click="drawer = true">•••</button>
        </div>
        <div class="welcome-collapsed-content">
          <div class="row grow">
            <div class="avatar avatar-small">🧚</div>
            <div>
              <b>发发·口袋发型设计助手</b
              ><span class="status-tag"><i></i>CONSULTING</span>
            </div>
          </div>
          <button class="menu-btn small" @click="drawer = true">•••</button>
        </div>
      </div>
    </header>
    <section class="upload-area">
      <div class="upload-row">
        <div
          class="upload-card"
          :class="uc"
          @click="pickUser"
          @mousedown="longPress"
          @mouseup="clearLong"
          @mouseleave="clearLong"
          @touchstart="longPress"
          @touchend="clearLong"
        >
          <template v-if="upUser"
            ><svg class="progress-ring" viewBox="0 0 36 36">
              <circle class="bg" cx="18" cy="18" r="16" />
              <circle
                class="fg"
                cx="18"
                cy="18"
                r="16"
                stroke-dasharray="100.53"
                :stroke-dashoffset="100.53 - (pct / 100) * 100.53"
              />
            </svg>
            <p>上传中 {{ pct }}%</p></template
          ><template v-else-if="user"
            ><img :src="user" />
            <div class="corner-wrap">
              <button @click.stop="replaceUser">↻</button
              ><button @click.stop="delUser">⌫</button>
            </div></template
          ><template v-else><b>＋</b><span>你的照片</span></template>
        </div>
        <div class="upload-card" :class="rc" @click="pickRef">
          <template v-if="upRef"
            ><b class="spin">✳</b>
            <p>上传中...</p></template
          ><template v-else-if="hair"
            ><img :src="hair" /><button
              class="corner-btn"
              @click.stop="refModal = true"
            >
              ⌫
            </button></template
          ><template v-else
            ><b>＋</b><span>参考发型</span><small>（可选）</small></template
          >
        </div>
      </div>
    </section>
    <input
      ref="uf"
      hidden
      type="file"
      accept="image/jpeg,image/png,image/webp"
      @change="onUser"
    /><input
      ref="rf"
      hidden
      type="file"
      accept="image/jpeg,image/png,image/webp"
      @change="onRef"
    />
    <main class="chat-area">
      <div v-for="m in msgs" :key="m.id" class="msg" :class="m.role">
        <div class="msg-avatar">{{ m.role === "user" ? "我" : "🧚" }}</div>
        <div v-if="m.type === 'text'" class="msg-content">
          <div class="bubble">{{ m.text }}</div>
          <time>{{ time(m.t) }}</time>
        </div>
        <div v-else-if="m.type === 'loading'" class="msg-content">
          <div class="loading-bubble">
            <p>{{ m.text }}</p>
            <div class="loading-dots">
              <span></span><span></span><span></span>
            </div>
          </div>
          <time>{{ time(m.t) }}</time>
        </div>
        <div v-else-if="m.type === 'image'" class="msg-content">
          <div class="bubble">{{ m.text }}</div>
          <img class="result-img" :src="m.image" />
          <div class="adjust-options">
            <button v-for="a in adjs" :key="a" @click="adjust(a)">
              {{ a }}
            </button>
          </div>
          <time>{{ time(m.t) }}</time>
        </div>
        <div v-else class="msg-content wide">
          <div class="bubble">{{ m.text }}</div>
          <time>{{ time(m.t) }}</time>
        </div>
      </div>
    </main>
    <footer class="bottom-bar">
      <div class="quick-tags hide-scrollbar">
        <button v-for="q in qs" :key="q[0]" @click="text = q[1]">
          {{ q[0] }}
        </button>
      </div>
      <div class="input-bar">
        <button class="voice" @click="toast('语音功能即将上线')">♩</button
        ><input
          v-model="text"
          placeholder="输入你想试的发型，比如'羊毛卷'"
          @keydown.enter="send"
        /><button
          class="send-btn"
          :class="{ active: text.trim() }"
          @click="send"
        >
          ➤
        </button>
      </div>
    </footer>
    <div
      class="drawer-overlay"
      :class="{ open: drawer }"
      @click="drawer = false"
    ></div>
    <aside class="drawer" :class="{ open: drawer }">
      <div class="drawer-header">
        <h2>设置</h2>
        <button @click="drawer = false">×</button>
      </div>
      <div class="drawer-user">
        <div>👤</div>
        <p>未登录</p>
      </div>
      <button
        @click="
          hist = true;
          drawer = false;
        "
      >
        历史对话 ›</button
      ><button class="danger" @click="clearModal = true">清除当前对话</button
      ><button>使用帮助</button><button>隐私政策</button>
      <footer>关于发发<br /><small>版本 v1.0.0</small></footer>
    </aside>
    <section class="history-page" :class="{ open: hist }">
      <div class="history-header">
        <button @click="hist = false">‹</button>
        <h2>历史对话</h2>
      </div>
      <div class="history-list">
        <div v-if="users.length < 1" class="history-empty">
          💬
          <p>还没有历史对话</p>
        </div>
        <div v-for="m in users" :key="m.id" class="history-item">
          <b>{{ m.text }}</b>
          <p>{{ time(m.t) }}</p>
        </div>
      </div>
    </section>
    <Modal
      :open="clearModal"
      title="确定清除当前对话？"
      desc="清除后无法恢复"
      @cancel="clearModal = false"
      @ok="clearChat"
    /><Modal
      :open="refModal"
      title="确定清除参考图？"
      desc="清除后无法恢复"
      @cancel="refModal = false"
      @ok="
        refModal = false;
        hair = '';
      "
    />
    <div
      class="sheet-overlay"
      :class="{ open: sheet }"
      @click.self="sheet = false"
    >
      <div class="sheet">
        <i></i><button @click="viewUser">查看大图</button
        ><button
          class="primary"
          @click="
            sheet = false;
            replaceUser();
          "
        >
          替换照片</button
        ><button
          class="danger"
          @click="
            sheet = false;
            delUser();
          "
        >
          删除照片
        </button>
      </div>
    </div>
    <div class="toast" :class="{ show: toasting }">{{ toastText }}</div>
  </div>
</template>
<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
const API = (import.meta.env.VITE_API_BASE || "http://localhost:8000").replace(
    /\/$/,
    ""
  ),
  sid = localStorage.getItem("hair_session_id") || crypto.randomUUID();
localStorage.setItem("hair_session_id", sid);
const qs = ref([
    ["锁骨短发", "推荐锁骨短发"],
    ["大波浪", "试戴大波浪"],
    ["显白发色", "推荐显白发色"],
    ["适合方脸", "什么发型适合方脸"],
    ["法式刘海", "试戴法式刘海"],
    ["羊毛卷", "试戴羊毛卷"],
  ]),
  adjs = ["颜色太深", "再短一点", "换一款"];
const uf = ref(),
  rf = ref(),
  top = ref(true),
  user = ref(""),
  hair = ref(""),
  file = ref(null),
  upUser = ref(false),
  upRef = ref(false),
  pct = ref(0),
  msgs = ref([]),
  text = ref(""),
  busy = ref(false),
  count = ref(0),
  drawer = ref(false),
  hist = ref(false),
  clearModal = ref(false),
  refModal = ref(false),
  sheet = ref(false),
  toastText = ref(""),
  toasting = ref(false),
  shake = ref(false);
let lpTimer, toastTimer, progressTimer;
const uc = computed(() => ({
    empty: !user.value && !upUser.value,
    uploading: upUser.value,
    shake: shake.value,
  })),
  rc = computed(() => ({
    empty: !hair.value && !upRef.value,
    uploading: upRef.value,
  })),
  users = computed(() => msgs.value.filter((x) => x.role === "user"));
function apiUrl(p) {
  return p && p.startsWith("http") ? p : API + p;
}
function setRecommendations(list, reply = "") {
  let source = Array.isArray(list) ? list : [];
  if (source.length === 0 && reply) {
    const line = reply
      .split(/\n+/)
      .find((item) => /推荐发型|适合发型|发型建议|推荐/.test(item));
    if (line) {
      source = line
        .replace(/^.*?[：:]/, "")
        .split(/[、，,；;]/)
        .map((item) =>
          item
            .replace(/^[\-•*\d\.、\)）\s]+/, "")
            .replace(/[：:].*$/, "")
            .trim()
        )
        .filter((item) => item.length >= 2 && item.length <= 12);
    }
  }
  if (source.length === 0) return;
  qs.value = source
    .map((item) => {
      const label = typeof item === "string" ? item : item.label || item.name;
      const value =
        typeof item === "string" ? `试戴${item}` : item.value || `试戴${label}`;
      return label ? [label, value] : null;
    })
    .filter(Boolean);
}
function add(x) {
  msgs.value.push({ id: Math.random(), t: Date.now(), ...x });
  requestAnimationFrame(() =>
    scrollTo({ top: document.body.scrollHeight, behavior: "smooth" })
  );
}
function time(t) {
  return new Date(t).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}
function scroll() {
  let y = scrollY || document.documentElement.scrollTop;
  if (top.value && y > 120) top.value = false;
  else if (!top.value && y < 20) top.value = true;
}
function pickUser() {
  if (!user.value && !upUser.value) uf.value.click();
}
function pickRef() {
  if (!hair.value && !upRef.value) rf.value.click();
}
function prog() {
  pct.value = 0;
  clearInterval(progressTimer);
  progressTimer = setInterval(() => {
    if (pct.value < 90) pct.value += 10;
  }, 300);
}
function done() {
  clearInterval(progressTimer);
  pct.value = 100;
  setTimeout(() => (upUser.value = false), 300);
}
async function post(path, fd) {
  let r = await fetch(API + path, { method: "POST", body: fd });
  if (!r.ok) throw new Error((await r.text()) || "接口请求失败");
  return r.json();
}
async function onUser(e) {
  let f = e.target.files[0];
  if (!f) return;
  if (!["image/jpeg", "image/png", "image/webp"].includes(f.type))
    return toast("请上传 jpg/png/webp 图片");
  if (f.size > 10485760) return toast("图片不能超过 10MB");
  file.value = f;
  user.value = URL.createObjectURL(f);
  upUser.value = true;
  prog();
  add({
    role: "assistant",
    type: "loading",
    text: "照片收到啦！正在分析脸型并生成推荐图像~",
  });
  try {
    let fd = new FormData();
    fd.append("session_id", sid);
    fd.append("image", f);
    fd.append("hair_desc", "适合当前脸型的自然时尚发型");
    let res = await post("/recommend", fd);
    setRecommendations(res.recommendations, res.reply);
    msgs.value.pop();
    add(
      res.image
        ? {
            role: "assistant",
            type: "image",
            text: res.reply || "已生成推荐发型效果图",
            image: apiUrl(res.image),
          }
        : {
            role: "assistant",
            type: "text",
            text: res.reply || "已完成分析，但没有返回图片",
          }
    );
  } catch (err) {
    msgs.value.pop();
    add({
      role: "assistant",
      type: "text",
      text: "上传或生成失败：" + err.message,
    });
  } finally {
    done();
  }
}
function onRef(e) {
  let f = e.target.files[0];
  if (!f) return;
  hair.value = URL.createObjectURL(f);
  toast("参考图已选择，后续可用于发型描述");
}
async function send() {
  let s = text.value.trim();
  if (!s || busy.value) return;
  add({ role: "user", type: "text", text: s });
  text.value = "";
  if ((s.includes("试戴") || s.includes("看看")) && !file.value) {
    shake.value = true;
    setTimeout(() => (shake.value = false), 300);
    setTimeout(
      () =>
        add({
          role: "assistant",
          type: "text",
          text: "先上传你的照片，我才能帮你试戴哦~ 📸",
        }),
      400
    );
    return;
  }
  busy.value = true;
  add({ role: "assistant", type: "loading", text: "正在处理..." });
  try {
    let fd = new FormData();
    fd.append("session_id", sid);
    fd.append("message", s);
    let res = await post("/chat", fd);
    msgs.value.pop();
    add(
      res.image
        ? {
            role: "assistant",
            type: "image",
            text: res.reply || "效果图生成完成",
            image: apiUrl(res.image),
          }
        : { role: "assistant", type: "text", text: res.reply || "已收到" }
    );
  } catch (err) {
    msgs.value.pop();
    add({ role: "assistant", type: "text", text: "请求失败：" + err.message });
  } finally {
    busy.value = false;
  }
}
function adjust(a) {
  if (count.value >= 5)
    return add({
      role: "assistant",
      type: "text",
      text: "已经调整很多次啦，建议换一款发型试试~",
    });
  count.value++;
  text.value = a;
  send();
}
function replaceUser() {
  user.value = "";
  file.value = null;
  uf.value.value = "";
  pickUser();
}
function delUser() {
  user.value = "";
  file.value = null;
}
function longPress() {
  if (user.value) lpTimer = setTimeout(() => (sheet.value = true), 500);
}
function clearLong() {
  clearTimeout(lpTimer);
}
function viewUser() {
  sheet.value = false;
  open(user.value, "_blank");
}
async function clearChat() {
  clearModal.value = false;
  drawer.value = false;
  msgs.value = [];
  count.value = 0;
  try {
    await fetch(API + "/session/" + sid, { method: "DELETE" });
  } catch {}
  add({
    role: "assistant",
    type: "text",
    text: "当前对话已清除。请上传照片，我帮你分析脸型并生成推荐发型。",
  });
}
function toast(s) {
  toastText.value = s;
  toasting.value = true;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (toasting.value = false), 2000);
}
onMounted(() => {
  add({
    role: "assistant",
    type: "text",
    text: "Hi，我是发发~ 你的专属 AI 发型顾问。上传你的照片，我会调用后端分析脸型并返回推荐发型效果图。",
  });
  addEventListener("scroll", scroll, { passive: true });
});
onUnmounted(() => {
  removeEventListener("scroll", scroll);
  clearInterval(progressTimer);
});
const Modal = {
  props: ["open", "title", "desc"],
  emits: ["cancel", "ok"],
  template: `<div class="modal-overlay" :class="{open}" @click.self="$emit('cancel')"><div class="modal"><h3>{{title}}</h3><p>{{desc}}</p><div><button @click="$emit('cancel')">取消</button><button class="confirm" @click="$emit('ok')">确定</button></div></div></div>`,
};
</script>
