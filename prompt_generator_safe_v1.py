import json
import random
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=self.text, justify="left",
            background="#fff8dc", relief="solid", borderwidth=1, padx=6, pady=4
        )
        label.pack()

    def hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class PromptGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Prompt Generator Safe v1")
        self.root.geometry("1500x980")
        self.root.minsize(1260, 860)

        self.base_dir = Path(__file__).resolve().parent
        self.config_path = self.base_dir / "prompt_config_safe_v1.json"
        self.config = self.load_config()

        self.style_mode = tk.StringVar(value="anime")
        self.lighting_mode = tk.StringVar(value="soft")
        self.cinema_mode = tk.StringVar(value=self.cfg("cinematic_presets_order")[0])
        self.constant_quality_var = tk.BooleanVar(value=True)
        self.lock_neg_var = tk.BooleanVar(value=False)

        self.dropdown_vars = {}
        self.lock_vars = {}
        self.ban_vars = {}
        self.comboboxes = {}
        self.selector_rows = {}
        self.last_negative = ""

        for key in ["ethnicity", "age_group", "hair_length", "accessory"]:
            if key in self.config["selectors"]:
                self.merge_random_pool(key)

        self._build_ui()
        self.lighting_mode.trace_add("write", self.update_cinema_state)
        self.root.bind_all("<space>", self.handle_space_generate)
        self.update_cinema_state()
        self.refresh_selector_styles()
        self.generate()

    def load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            messagebox.showerror("錯誤", f"找不到設定檔：{self.config_path.name}")
            raise
        except json.JSONDecodeError as e:
            messagebox.showerror("錯誤", f"設定檔 JSON 格式錯誤：\n{e}")
            raise

    def merge_random_pool(self, key):
        opts = self.cfg("selectors", key, "options")
        merged = []
        for name, vals in opts.items():
            if name == "隨機":
                continue
            for tag in vals:
                if tag not in merged:
                    merged.append(tag)
        opts["隨機"] = merged

    def cfg(self, *keys):
        data = self.config
        for key in keys:
            data = data[key]
        return data

    def has_cfg(self, *keys):
        data = self.config
        for key in keys:
            if not isinstance(data, dict) or key not in data:
                return False
            data = data[key]
        return True

    def pick(self, pool):
        return random.choice(pool)

    def sample(self, pool, c):
        return random.sample(pool, max(0, min(c, len(pool))))

    def contains_cjk(self, text):
        return any("\u4e00" <= ch <= "\u9fff" for ch in text)

    def normalize_result(self, result):
        if result is None:
            return []
        if isinstance(result, list):
            return [t for t in result if isinstance(t, str) and t.strip() and not self.contains_cjk(t)]
        if isinstance(result, str):
            if result.strip() and not self.contains_cjk(result):
                return [result]
        return []

    def add_result(self, bucket, result):
        bucket.extend(self.normalize_result(result))

    def get_banned_tags(self):
        banned = set()
        for key, ban_var in self.ban_vars.items():
            if not ban_var.get():
                continue
            current = self.dropdown_vars[key].get()
            if current == "隨機":
                continue
            try:
                tags = self.cfg("selectors", key, "options", current)
            except Exception:
                tags = []
            if isinstance(tags, list):
                for t in tags:
                    if isinstance(t, str):
                        banned.add(t)
        return banned

    def flash_status(self, msg):
        self.status_label.config(text=msg, foreground="blue")
        self.root.after(1500, lambda: self.status_label.config(text="Ready", foreground="gray"))

    def flash_combo(self, key):
        box = self.comboboxes.get(key)
        if not box:
            return
        try:
            old_style = box.cget("style")
        except Exception:
            old_style = "TCombobox"
        box.configure(style="Highlight.TCombobox")
        self.root.after(350, lambda: box.configure(style=old_style))

    def _register_style_watch(self, lock_var, ban_var):
        def callback(*_):
            self.refresh_selector_styles()
        lock_var.trace_add("write", callback)
        ban_var.trace_add("write", callback)

    def _build_selector(self, parent, row, label, key, options):
        ttk.Label(parent, text=label, width=12).grid(row=row, column=0, sticky="w", padx=(4, 6), pady=4)

        var = tk.StringVar(value="隨機")
        box = ttk.Combobox(parent, textvariable=var, values=list(options.keys()), state="readonly", width=12)
        box.grid(row=row, column=1, sticky="ew", pady=4)

        lock_var = tk.BooleanVar(value=False)
        ban_var = tk.BooleanVar(value=False)

        lock_btn = ttk.Checkbutton(parent, text="🔒", variable=lock_var, takefocus=False)
        lock_btn.grid(row=row, column=2, padx=(6, 0), sticky="w")
        ToolTip(lock_btn, "鎖定此分類：之後抽選時固定使用這個分類")

        ban_btn = ttk.Checkbutton(parent, text="🚫", variable=ban_var, takefocus=False)
        ban_btn.grid(row=row, column=3, padx=(6, 0), sticky="w")
        ToolTip(ban_btn, "禁用此分類：之後抽選時不再抽到這個分類的提示詞")

        parent.grid_columnconfigure(1, weight=1)
        self.dropdown_vars[key] = var
        self.lock_vars[key] = lock_var
        self.ban_vars[key] = ban_var
        self.comboboxes[key] = box
        self.selector_rows[key] = {"box": box, "var": var}
        self._register_style_watch(lock_var, ban_var)

    def _build_ui(self):
        style = ttk.Style()
        try:
            style.configure("Highlight.TCombobox", fieldbackground="#fff6cc")
            style.configure("Locked.TCombobox", fieldbackground="#e7f4ff")
            style.configure("Banned.TCombobox", fieldbackground="#eeeeee")
        except Exception:
            pass

        top = ttk.LabelFrame(self.root, text="控制面板（Safe）", padding=10)
        top.pack(fill="x", padx=10, pady=6)

        ttk.Label(top, text="風格").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(top, text="動漫", variable=self.style_mode, value="anime").grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(top, text="寫實", variable=self.style_mode, value="realistic").grid(row=0, column=2, sticky="w")

        ttk.Label(top, text="光線").grid(row=0, column=3, padx=(18, 0), sticky="w")
        ttk.Combobox(top, textvariable=self.lighting_mode, values=["soft", "strong", "mixed", "cinematic"], width=12, state="readonly").grid(row=0, column=4, sticky="w")

        ttk.Label(top, text="電影感預設").grid(row=1, column=0, pady=(10, 0), sticky="w")
        self.cinema_box = ttk.Combobox(top, textvariable=self.cinema_mode, values=self.cfg("cinematic_presets_order"), width=18, state="readonly")
        self.cinema_box.grid(row=1, column=1, columnspan=2, pady=(10, 0), sticky="w")
        ttk.Checkbutton(top, text="畫質標籤", variable=self.constant_quality_var, takefocus=False).grid(row=1, column=3, pady=(10, 0), sticky="w")
        ttk.Checkbutton(top, text="鎖定負面", variable=self.lock_neg_var, takefocus=False).grid(row=1, column=4, pady=(10, 0), sticky="w")

        action_frame = ttk.Frame(top)
        action_frame.grid(row=0, column=6, rowspan=2, sticky="ne", padx=(24, 0))
        ttk.Button(action_frame, text="🎲 抽選", command=self.generate, takefocus=False, width=12).pack(side="top", anchor="e")
        ttk.Button(action_frame, text="📋 複製全部", command=self.copy_all, takefocus=False, width=12).pack(side="top", anchor="e", pady=(8, 0))

        self.general_tab = ttk.LabelFrame(self.root, text="一般分類", padding=10)
        self.general_tab.pack(fill="x", padx=10, pady=6)

        header = ttk.Frame(self.general_tab)
        header.pack(fill="x", pady=(0, 6))
        ttk.Button(header, text="全隨機", command=self.reset_all_selectors, takefocus=False).pack(side="right")
        ttk.Button(header, text="全解鎖", command=self.unlock_all, takefocus=False).pack(side="right", padx=5)
        ttk.Button(header, text="全鎖定", command=self.lock_all, takefocus=False).pack(side="right", padx=5)

        content = ttk.Frame(self.general_tab)
        content.pack(fill="x")
        cols = [ttk.Frame(content) for _ in range(4)]
        for c in cols:
            c.pack(side="left", fill="both", expand=True, padx=6)

        sel = self.cfg("selectors")
        groups = [
            ["ethnicity", "age_group", "composition_distance", "camera_angle", "pose_template"],
            ["body_pose", "expression", "hair_color", "hair_length"],
            ["hair_texture", "hair_front", "eye_color", "hand_action"],
            ["outfit_style", "outfit_template", "accessory", "background", "atmosphere"]
        ]
        for col_idx, group in enumerate(groups):
            for row, key in enumerate(group):
                self._build_selector(cols[col_idx], row, sel[key]["label"], key, sel[key]["options"])

        hint = ttk.Frame(self.root, padding=(12, 0, 12, 0))
        hint.pack(fill="x")
        ttk.Label(hint, text="Safe 版已移除 NSFW 與高風險內容。🔒 固定分類　🚫 禁用分類", foreground="gray").pack(anchor="w")

        preview = ttk.Frame(self.root, padding=10)
        preview.pack(fill="both", expand=True)

        pos_wrap = ttk.LabelFrame(preview, text="正面提示詞（預覽）", padding=10)
        pos_wrap.pack(fill="both", expand=True, pady=(0, 6))
        pos_top = ttk.Frame(pos_wrap)
        pos_top.pack(fill="x", pady=(0, 6))
        ttk.Button(pos_top, text="展開", command=self.show_full_positive, takefocus=False).pack(side="right")
        ttk.Button(pos_top, text="複製正面", command=self.copy_positive, takefocus=False).pack(side="right", padx=(0, 8))
        self.prompt_text = tk.Text(pos_wrap, height=8, font=("Menlo", 12), wrap="word")
        self.prompt_text.pack(fill="both", expand=True)

        neg_wrap = ttk.LabelFrame(preview, text="負面提示詞（預覽）", padding=10)
        neg_wrap.pack(fill="both", expand=False)
        neg_top = ttk.Frame(neg_wrap)
        neg_top.pack(fill="x", pady=(0, 6))
        ttk.Button(neg_top, text="展開", command=self.show_full_negative, takefocus=False).pack(side="right")
        ttk.Button(neg_top, text="複製負面", command=self.copy_negative, takefocus=False).pack(side="right", padx=(0, 8))
        self.neg_text = tk.Text(neg_wrap, height=4, font=("Menlo", 12), wrap="word", fg="gray")
        self.neg_text.pack(fill="both", expand=False)

        bottom = ttk.Frame(self.root, padding=10)
        bottom.pack(fill="x")
        self.status_label = ttk.Label(bottom, text="Ready", foreground="gray")
        self.status_label.pack(side="right")

    def refresh_selector_styles(self):
        for key, row in self.selector_rows.items():
            box = row["box"]
            if self.ban_vars[key].get():
                box.configure(style="Banned.TCombobox", state="disabled")
            else:
                box.configure(state="readonly")
                if self.lock_vars[key].get():
                    box.configure(style="Locked.TCombobox")
                else:
                    box.configure(style="TCombobox")

    def update_cinema_state(self, *args):
        enabled = self.lighting_mode.get() == "cinematic"
        self.cinema_box.configure(state="readonly" if enabled else "disabled")

    def unlock_all(self):
        for v in self.lock_vars.values():
            v.set(False)
        self.refresh_selector_styles()
        self.flash_status("一般分類已全部解鎖")

    def lock_all(self):
        for v in self.lock_vars.values():
            v.set(True)
        self.refresh_selector_styles()
        self.flash_status("一般分類已全部鎖定")

    def reset_all_selectors(self):
        for key, var in self.dropdown_vars.items():
            var.set("隨機")
            self.ban_vars[key].set(False)
        self.refresh_selector_styles()
        self.flash_status("一般分類已回到隨機")

    def show_text_popup(self, title, content):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("1000x460")
        top = ttk.Frame(win, padding=10)
        top.pack(fill="x")
        ttk.Button(top, text="複製", command=lambda: self.copy_text(content), takefocus=False).pack(side="right")
        text = tk.Text(win, wrap="word", font=("Menlo", 12))
        text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        text.insert("1.0", content)
        text.configure(state="disabled")

    def show_full_positive(self):
        self.show_text_popup("完整正面提示詞", self.prompt_text.get("1.0", "end").strip())

    def show_full_negative(self):
        self.show_text_popup("完整負面提示詞", self.neg_text.get("1.0", "end").strip())

    def handle_space_generate(self, e=None):
        if isinstance(self.root.focus_get(), (tk.Text, tk.Entry, ttk.Combobox)):
            return
        self.generate()
        return "break"

    def copy_text(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def copy_positive(self):
        self.copy_text(self.prompt_text.get("1.0", "end").strip())
        self.flash_status("已複製正面提示詞")

    def copy_negative(self):
        self.copy_text(self.neg_text.get("1.0", "end").strip())
        self.flash_status("已複製負面提示詞")

    def copy_all(self):
        res = f"Positive:\n{self.prompt_text.get('1.0', 'end').strip()}\n\nNegative:\n{self.neg_text.get('1.0', 'end').strip()}"
        self.copy_text(res)
        self.flash_status("已複製全部")

    def choose_tag(self, key):
        cfg = self.cfg("selectors", key, "options")
        var = self.dropdown_vars[key]
        lock_var = self.lock_vars[key]
        ban_var = self.ban_vars[key]
        domain_banned = self.get_banned_tags()

        current = var.get()
        random_pool = list(cfg["隨機"])
        option_names = {name for name in cfg.keys() if name != "隨機"}
        random_is_option_names = all(item in option_names for item in random_pool)

        if random_is_option_names:
            filtered_options = []
            for option_name in random_pool:
                option_tags = cfg.get(option_name, [])
                if option_name == "無":
                    filtered_options.append(option_name)
                elif any(t not in domain_banned for t in option_tags):
                    filtered_options.append(option_name)
            if filtered_options:
                random_pool = filtered_options
        else:
            filtered_tags = [x for x in random_pool if x not in domain_banned]
            if filtered_tags:
                random_pool = filtered_tags

        if ban_var.get() and current != "隨機":
            if random_is_option_names:
                filtered = [x for x in random_pool if x != current]
            else:
                banned_tags = set(cfg.get(current, []))
                filtered = [x for x in random_pool if x not in banned_tags]
            if filtered:
                random_pool = filtered

        if lock_var.get():
            picked = current if current != "隨機" else self.pick(random_pool)
            if picked == "無":
                return []
            if picked in cfg and picked != "隨機":
                result = cfg.get(picked, [])
                return [t for t in result if t not in domain_banned]
            for option_name, tags in cfg.items():
                if option_name == "隨機":
                    continue
                if picked in tags:
                    return [t for t in tags if t not in domain_banned]
            return []

        picked = self.pick(random_pool)

        if picked == "無":
            var.set("無")
            self.flash_combo(key)
            return []

        if picked in cfg and picked != "隨機":
            var.set(picked)
            self.flash_combo(key)
            result = cfg.get(picked, [])
            if isinstance(result, list):
                result = [t for t in result if t not in domain_banned]
            return result

        for option_name, tags in cfg.items():
            if option_name == "隨機":
                continue
            if picked in tags:
                var.set(option_name)
                self.flash_combo(key)
                return [t for t in tags if t not in domain_banned]

        return []

    def resolve_conflicts(self, tags):
        tags = [t for t in tags if isinstance(t, str) and t.strip() and not self.contains_cjk(t)]

        outfit_template_tags = {
            "cropped shirt", "micro skirt", "belted skirt", "thigh strap", "arm warmers",
            "fingerless gloves", "punk style", "streetwear",
            "black dress", "long gloves", "lace choker", "elegant outfit"
        }
        outfit_style_tags = {
            "dress", "school uniform", "shirt", "sweater", "hoodie", "jacket", "coat",
            "bikini", "one-piece swimsuit", "maid outfit", "cheongsam",
            "kimono", "nurse outfit", "office lady", "yukata"
        }
        if any(t in tags for t in outfit_template_tags):
            tags = [t for t in tags if t not in outfit_style_tags]

        base_pose_tags = {"standing", "sitting", "lying", "walking"}
        if "kneeling" in tags:
            tags = [t for t in tags if t not in base_pose_tags and t not in {"squatting", "casual stance"}]
        if "squatting" in tags:
            tags = [t for t in tags if t not in base_pose_tags and t not in {"kneeling"}]
        if "lying on side" in tags:
            tags = [t for t in tags if t not in {"standing", "sitting", "walking", "kneeling", "squatting", "lying"}]
        if any(t in tags for t in {"leaning", "one leg raised", "casual stance"}):
            tags = [t for t in tags if t not in {"sitting", "walking", "lying", "kneeling", "squatting"}]

        seen = set()
        final = []
        for t in tags:
            if t not in seen:
                seen.add(t)
                final.append(t)
        return final

    def build_positive(self):
        tags = []
        if self.has_cfg("quality") and self.constant_quality_var.get():
            tags += self.cfg("quality")
        tags += self.cfg("subject")
        tags += self.cfg("style_main", self.style_mode.get())

        general_order = [
            "ethnicity", "age_group", "composition_distance", "camera_angle",
            "body_pose", "pose_template", "expression", "hair_color", "hair_length",
            "hair_texture", "hair_front", "eye_color", "hand_action",
            "outfit_style", "outfit_template", "accessory", "background", "atmosphere"
        ]
        for key in general_order:
            self.add_result(tags, self.choose_tag(key))

        if self.has_cfg("face_detail"):
            tags += self.sample(self.cfg("face_detail"), 3)

        lm = self.lighting_mode.get()
        tags += self.sample(self.cfg("light_strength", lm), min(2, len(self.cfg("light_strength", lm))))
        tags += self.sample(self.cfg("light_direction"), 1)
        tags += self.sample(self.cfg("light_effect"), 2)
        if lm == "cinematic":
            tags += self.cfg("cinematic_presets", self.cinema_mode.get())

        final = self.resolve_conflicts([t.strip() for t in tags if t])
        final = [t for t in final if t not in self.get_banned_tags()]
        return ", ".join(final[: int(self.cfg("meta", "max_positive_tags"))])

    def build_negative(self):
        if self.lock_neg_var.get() and self.last_negative:
            return self.last_negative
        n = (
            self.cfg("negative_base")
            + self.cfg("negative_by_style", self.style_mode.get())
            + self.cfg("negative_by_light", self.lighting_mode.get())
        )
        result = ", ".join(dict.fromkeys(n))
        self.last_negative = result
        return result

    def generate(self):
        if self.lock_neg_var.get():
            current_neg = self.neg_text.get("1.0", "end").strip()
            if current_neg:
                self.last_negative = current_neg

        pos_result = self.build_positive()
        neg_result = self.build_negative()

        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", pos_result)

        self.neg_text.delete("1.0", "end")
        self.neg_text.insert("1.0", neg_result)

        self.prompt_text.see("1.0")
        self.refresh_selector_styles()
        self.flash_status("已重新抽選")


def main():
    root = tk.Tk()
    PromptGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
