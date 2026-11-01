/* 人脸遮罩验证脚本：在课程播放页的 DevTools Console 里整段粘贴运行。
 *
 * 作用：隐藏人脸遮罩 → 观察 12 秒 → 告诉你这个采集是"纸老虎"还是"强制采集"。
 * 不改动服务端任何数据，只操作当前页面 DOM。
 *
 * 用法：
 *   1. 用程序把课程打开到会弹人脸的那一页（或自己手动进章节页），等遮罩出现；
 *   2. F12 → Console → 粘贴本文件全部内容 → 回车；
 *   3. 读最后两行输出，按 docs 里的判读表处理。
 */
(async () => {
  const SEL = '.chapterVideoFaceMaskDiv,.chapterVideoFaceQrMaskDiv,.maskDiv';

  const isFace = (e) =>
    e.matches('.chapterVideoFaceMaskDiv,.chapterVideoFaceQrMaskDiv') ||
    /人脸|采集|活体/.test(e.textContent || '') ||
    !!e.querySelector('#fcqrimg');

  const visible = (root) =>
    Array.from(root.querySelectorAll(SEL)).filter((e) => {
      if (!isFace(e)) return false;
      const s = getComputedStyle(e);
      return s.display !== 'none' && s.visibility !== 'hidden' && e.getClientRects().length > 0;
    });

  const hide = (root) => {
    let n = 0;
    visible(root).forEach((e) => {
      e.style.display = 'none';
      e.setAttribute('data-probe-hidden', '1');
      n++;
    });
    return n;
  };

  // 遮罩可能在 iframe 里；跨域会抛，跳过即可
  const docs = () => {
    const out = [{ name: 'top', doc: document }];
    document.querySelectorAll('iframe').forEach((f, i) => {
      try {
        if (f.contentDocument) out.push({ name: 'iframe[' + i + '] ' + (f.src || ''), doc: f.contentDocument });
      } catch (e) { /* cross-origin */ }
    });
    return out;
  };

  const playTime = () => {
    for (const d of docs()) {
      const el = d.doc.querySelector('.vjs-current-time-display');
      if (el) return d.name + ' | ' + (el.textContent || '').trim();
    }
    return '(没有视频进度条)';
  };

  console.log('%c[诊断] URL', 'color:#08f', location.href);
  Array.from(document.querySelectorAll('iframe')).forEach((f, i) =>
    console.log('%c[诊断] iframe[' + i + '] src=', 'color:#08f', f.src || '(空)'));

  const hit = docs().map((d) => ({ name: d.name, n: visible(d.doc).length })).filter((x) => x.n > 0);
  if (!hit.length) {
    console.log('%c当前页面没有可见的人脸遮罩：说明此刻没有触发采集，先等它弹出来再跑一次。', 'color:#e90;font-weight:bold');
    return;
  }
  console.log('%c检测到遮罩：', 'color:#e90;font-weight:bold', hit);

  const t0 = playTime();
  hit.forEach((h) => {
    const d = docs().find((x) => x.name === h.name);
    hide(d.doc);
  });

  let back = 0;
  const timer = setInterval(() => {
    let n = 0;
    docs().forEach((d) => { n += hide(d.doc); });
    if (n > 0) back++;
  }, 1000);

  await new Promise((r) => setTimeout(r, 12000));
  clearInterval(timer);

  const t1 = playTime();
  const left = docs().reduce((s, d) => s + visible(d.doc).length, 0);

  console.log('%c[结果] 弹窗被推回次数：' + back + ' | 剩余可见遮罩：' + left, 'color:#08f');
  console.log('%c[结果] 播放时间：' + t0 + '  ->  ' + t1, 'color:#08f');

  if (back === 0 && left === 0) {
    console.log('%c✅ 纸老虎：遮罩藏掉后 12 秒没被服务端推回。', 'color:#0a0;font-weight:bold;font-size:14px');
    console.log('%c   下一步看任务点图标是否变绿 / 进度是否继续走；走 = 真的能跳过。', 'color:#0a0');
  } else if (left > 0) {
    console.log('%c❌ 强制采集：服务端/心跳在重推遮罩，前端藏不住。', 'color:#c00;font-weight:bold;font-size:14px');
    console.log('%c   下一步测"换入口"：复制上面 iframe 的 src，新标签页打开，看还弹不弹。', 'color:#c00');
  } else if (t0 === t1) {
    console.log('%c❌ 遮罩藏掉了但播放停住：服务端暂停了播放器，属于强制采集。', 'color:#c00;font-weight:bold;font-size:14px');
  } else {
    console.log('%c⚠️ 结果不明：遮罩没回弹，但播放时间也拿不到。看任务点图标是否推进。', 'color:#e90;font-weight:bold;font-size:14px');
  }
})();
