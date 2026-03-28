
import json
import random
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path


class PromptGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Prompt Generator v23.6 fixed")
        self.root.geometry("1560x1020")
        self.root.minsize(1300, 900)

        self.base_dir = Path(__file__).resolve().parent
        self.config_path = self.base_dir / "prompt_config_v23_6_fixed.json"
        self.config = self.load_config()

        self.style_mode = tk.StringVar(value="anime")
        self.lighting_mode = tk.StringVar(value="soft")
        self.cinema_mode = tk.StringVar(value=self.cfg("cinematic_presets_order")[0])
        self.constant_quality_var = tk.BooleanVar(value=True)
        self.lock_neg_var = tk.BooleanVar(value=False)
        self.nsfw_mode = tk.StringVar(value="off")

        self.dropdown_vars = {}
        self.lock_vars = {}
        self.ban_vars = {}
        self.nsfw_dropdown_vars = {}
        self.nsfw_lock_vars = {}
        self.nsfw_ban_vars = {}
        self.comboboxes = {}
        self.nsfw_comboboxes = {}
        self.last_negative = ""

        # Auto-merge random pools so all categories participate
        self.merge_random_pool("ethnicity")
        self.merge_random_pool("age_group")

        self._build_ui()
        self.nsfw_mode.trace_add("write", self.update_nsfw_tab_state)
        self.lighting_mode.trace_add("write", self.update_cinema_state)
        self.root.bind_all("<space>", self.handle_space_generate)
        self.update_nsfw_tab_state()
        self.update_cinema_state()
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

    def flash_status(self, msg):
        self.status_label.config(text=msg, foreground="blue")
        self.root.after(1500, lambda: self.status_label.config(text="Ready", foreground="gray"))

    def flash_combo(self, key, is_nsfw=False):
        box_map = self.nsfw_comboboxes if is_nsfw else self.comboboxes
        box = box_map.get(key)
        if not box:
            return
        try:
            old_style = box.cget("style")
        except Exception:
            old_style = "TCombobox"
        box.configure(style="Highlight.TCombobox")
        self.root.after(350, lambda: box.configure(style=old_style))

    def _build_selector(self, parent, row, label, key, options, is_nsfw=False):
        ttk.Label(parent, text=label, width=12).grid(row=row, column=0, sticky="w", padx=(4, 6), pady=4)
        var = tk.StringVar(value="隨機")
        box = ttk.Combobox(parent, textvariable=var, values=list(options.keys()), state="readonly", width=12)
        box.grid(row=row, column=1, sticky="ew", pady=4)
        lock_var = tk.BooleanVar(value=False)
        ban_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(parent, text="鎖", variable=lock_var, takefocus=False).grid(
            row=row, column=2, padx=(6, 0), sticky="w"
        )
        ttk.Checkbutton(parent, text="ban", variable=ban_var, takefocus=False).grid(
            row=row, column=3, padx=(6, 0), sticky="w"
        )
        parent.grid_columnconfigure(1, weight=1)
        if is_nsfw:
            self.nsfw_dropdown_vars[key] = var
            self.nsfw_lock_vars[key] = lock_var
            self.nsfw_ban_vars[key] = ban_var
            self.nsfw_comboboxes[key] = box
        else:
            self.dropdown_vars[key] = var
            self.lock_vars[key] = lock_var
            self.ban_vars[key] = ban_var
            self.comboboxes[key] = box

    def _build_ui(self):
        style = ttk.Style()
        try:
            style.configure("Highlight.TCombobox", fieldbackground="#fff6cc")
        except Exception:
            pass

        top = ttk.LabelFrame(self.root, text="控制面板", padding=10)
        top.pack(fill="x", padx=10, pady=6)

        for col in range(8):
            top.grid_columnconfigure(col, weight=0)
        top.grid_columnconfigure(7, weight=1)

        ttk.Label(top, text="風格").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(top, text="動漫", variable=self.style_mode, value="anime").grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(top, text="寫實", variable=self.style_mode, value="realistic").grid(row=0, column=2, sticky="w")

        ttk.Label(top, text="NSFW").grid(row=0, column=3, padx=(18, 0), sticky="w")
        ttk.Combobox(top, textvariable=self.nsfw_mode, values=["off", "light", "medium", "heavy"], width=10, state="readonly").grid(row=0, column=4, sticky="w")

        ttk.Label(top, text="光線").grid(row=0, column=5, padx=(18, 0), sticky="w")
        ttk.Combobox(top, textvariable=self.lighting_mode, values=["soft", "strong", "mixed", "cinematic"], width=12, state="readonly").grid(row=0, column=6, sticky="w")

        action_frame = ttk.Frame(top)
        action_frame.grid(row=0, column=7, rowspan=2, sticky="ne", padx=(24, 0))
        ttk.Button(action_frame, text="🎲 抽選", command=self.generate, takefocus=False, width=12).pack(side="top", anchor="e")
        ttk.Button(action_frame, text="📋 複製全部", command=self.copy_all, takefocus=False, width=12).pack(side="top", anchor="e", pady=(8, 0))

        ttk.Label(top, text="電影感預設").grid(row=1, column=0, pady=(10, 0), sticky="w")
        self.cinema_box = ttk.Combobox(top, textvariable=self.cinema_mode, values=self.cfg("cinematic_presets_order"), width=18, state="readonly")
        self.cinema_box.grid(row=1, column=1, columnspan=2, pady=(10, 0), sticky="w")
        ttk.Checkbutton(top, text="畫質標籤", variable=self.constant_quality_var, takefocus=False).grid(row=1, column=3, pady=(10, 0), sticky="w")
        ttk.Checkbutton(top, text="鎖定負面", variable=self.lock_neg_var, takefocus=False).grid(row=1, column=4, pady=(10, 0), sticky="w")
        self.cinema_hint = ttk.Label(top, text="僅在光線 = cinematic 時生效")
        self.cinema_hint.grid(row=1, column=5, columnspan=2, pady=(10, 0), sticky="w")

        tab_wrap = ttk.Frame(self.root, padding=(10, 4, 10, 0))
        tab_wrap.pack(fill="x")

        self.notebook = ttk.Notebook(tab_wrap)
        self.notebook.pack(fill="x")

        self.general_tab = ttk.Frame(self.notebook, padding=10)
        self.nsfw_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.general_tab, text="一般分類")
        self.notebook.add(self.nsfw_tab, text="NSFW 分類")

        self._build_general_tab()
        self._build_nsfw_tab()

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

    def _build_general_tab(self):
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
            ["ethnicity", "age_group", "composition_distance", "camera_angle"],
            ["body_pose", "expression", "hair_color", "hair_length"],
            ["hair_texture", "hair_front", "eye_color", "hand_action"],
            ["outfit_style", "accessory", "background", "atmosphere"]
        ]
        for col_idx, group in enumerate(groups):
            for row, key in enumerate(group):
                self._build_selector(cols[col_idx], row, sel[key]["label"], key, sel[key]["options"])

    def _build_nsfw_tab(self):
        header = ttk.Frame(self.nsfw_tab)
        header.pack(fill="x", pady=(0, 6))
        ttk.Button(header, text="全隨機", command=self.reset_nsfw, takefocus=False).pack(side="right")
        ttk.Button(header, text="全解鎖", command=self.unlock_nsfw, takefocus=False).pack(side="right", padx=5)
        ttk.Button(header, text="全鎖定", command=self.lock_nsfw, takefocus=False).pack(side="right", padx=5)

        content = ttk.Frame(self.nsfw_tab)
        content.pack(fill="x")

        cols = [ttk.Frame(content) for _ in range(3)]
        for c in cols:
            c.pack(side="left", fill="both", expand=True, padx=6)

        ns = self.cfg("nsfw_selectors")
        groups = [
            ["nsfw_camera", "focus_area", "nsfw_pose_action"],
            ["areola_detail", "breast_pressure", "breast_size", "wetness_source",
"wetness_effect"],
            ["private_detail", "foot_detail", "fetish_focus", "hand_nsfw"]
        ]
        for col_idx, group in enumerate(groups):
            for row, key in enumerate(group):
                self._build_selector(cols[col_idx], row, ns[key]["label"], key, ns[key]["options"], is_nsfw=True)

    def update_cinema_state(self, *args):
        enabled = self.lighting_mode.get() == "cinematic"
        self.cinema_box.configure(state="readonly" if enabled else "disabled")
        self.cinema_hint.configure(text="目前已啟用" if enabled else "僅在光線 = cinematic 時生效")

    def update_nsfw_tab_state(self, *args):
        mode = self.nsfw_mode.get()
        idx = self.notebook.index(self.nsfw_tab)
        if mode == "off":
            self.notebook.tab(idx, state="disabled")
            if self.notebook.index("current") == idx:
                self.notebook.select(self.general_tab)
        else:
            self.notebook.tab(idx, state="normal")

    def unlock_all(self):
        for v in self.lock_vars.values():
            v.set(False)
        self.flash_status("一般分類已全部解鎖")

    def lock_all(self):
        for v in self.lock_vars.values():
            v.set(True)
        self.flash_status("一般分類已全部鎖定")

    def reset_all_selectors(self):
        for key, var in self.dropdown_vars.items():
            var.set("隨機")
            self.ban_vars[key].set(False)
        self.flash_status("一般分類已回到隨機")

    def lock_nsfw(self):
        for v in self.nsfw_lock_vars.values():
            v.set(True)
        self.flash_status("NSFW 已全部鎖定")

    def unlock_nsfw(self):
        for v in self.nsfw_lock_vars.values():
            v.set(False)
        self.flash_status("NSFW 已全部解鎖")

    def reset_nsfw(self):
        for key, var in self.nsfw_dropdown_vars.items():
            var.set("隨機")
            self.nsfw_ban_vars[key].set(False)
        self.flash_status("NSFW 已全部重設")

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

    def choose_tag(self, key, is_nsfw=False):
        if is_nsfw:
            cfg = self.cfg("nsfw_selectors", key, "options")
            var = self.nsfw_dropdown_vars[key]
            lock_var = self.nsfw_lock_vars[key]
            ban_var = self.nsfw_ban_vars[key]
        else:
            cfg = self.cfg("selectors", key, "options")
            var = self.dropdown_vars[key]
            lock_var = self.lock_vars[key]
            ban_var = self.ban_vars[key]

        current = var.get()

        allowed = list(cfg["隨機"])
        if ban_var.get() and current != "隨機":
            banned_tags = set(cfg.get(current, []))
            filtered = [t for t in allowed if t not in banned_tags]
            if filtered:
                allowed = filtered

        if lock_var.get():
            if current == "隨機":
                return self.pick(allowed)
            pool = list(cfg.get(current, []))
            if ban_var.get():
                pool = [t for t in pool if t not in cfg.get(current, [])]
            if not pool:
                pool = allowed
            return self.pick(pool)

        picked = self.pick(allowed)
        matched = False
        for option_name, tags in cfg.items():
            if option_name == "隨機":
                continue
            if picked in tags:
                var.set(option_name)
                self.flash_combo(key, is_nsfw=is_nsfw)
                matched = True
                break
        if not matched:
            var.set("隨機")
        return picked

    def build_positive(self):
        p = []
        if self.has_cfg("quality") and self.constant_quality_var.get():
            p += self.cfg("quality")
        p += self.cfg("subject")
        p += self.cfg("style_main", self.style_mode.get())

        general_order = [
            "ethnicity", "age_group", "composition_distance", "camera_angle",
            "body_pose", "expression", "hair_color", "hair_length",
            "hair_texture", "hair_front", "eye_color", "hand_action",
            "outfit_style", "accessory", "background", "atmosphere"
        ]
        for key in general_order:
            p.append(self.choose_tag(key))

        if self.has_cfg("face_detail"):
            p += self.sample(self.cfg("face_detail"), 3)

        nsfw = self.nsfw_mode.get()
        if nsfw != "off":
            nsfw_order = [
                "nsfw_camera", "focus_area", "nsfw_pose_action",
                "areola_detail", "breast_pressure", "breast_size",
                "private_detail", "foot_detail", "fetish_focus",
                "wetness_source",
                "wetness_effect", "hand_nsfw"
            ]
            density = self.cfg("meta", "nsfw_density", nsfw)
            keys = nsfw_order[:density]
            for key in keys:
                p.append(self.choose_tag(key, is_nsfw=True))

            p += self.sample(self.cfg("nsfw", nsfw, "positive"), min(2, len(self.cfg("nsfw", nsfw, "positive"))))
            if nsfw == "heavy":
                p += self.sample(self.cfg("nsfw", "heavy", "exposure_focus"), 1)
                p += self.sample(self.cfg("nsfw", "heavy", "camera_bias"), 1)

        lm = self.lighting_mode.get()
        p += self.sample(self.cfg("light_strength", lm), min(2, len(self.cfg("light_strength", lm))))
        if nsfw != "off" and self.has_cfg("nsfw", nsfw, "light_bonus"):
            p += self.sample(self.cfg("nsfw", nsfw, "light_bonus"), min(1, len(self.cfg("nsfw", nsfw, "light_bonus"))))
        p += self.sample(self.cfg("light_direction"), 1)
        p += self.sample(self.cfg("light_effect"), 2)
        if lm == "cinematic":
            p += self.cfg("cinematic_presets", self.cinema_mode.get())

        seen, final = set(), []
        for tag in [t.strip() for t in p if t]:
            if tag not in seen:
                seen.add(tag)
                final.append(tag)
        return ", ".join(final[: int(self.cfg("meta", "max_positive_tags"))])

    def build_negative(self):
        if self.lock_neg_var.get() and self.last_negative:
            return self.last_negative

        n = (
            self.cfg("negative_base")
            + self.cfg("negative_by_style", self.style_mode.get())
            + self.cfg("negative_by_light", self.lighting_mode.get())
        )
        if self.nsfw_mode.get() != "off":
            n += self.cfg("nsfw", self.nsfw_mode.get(), "negative")

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
        self.flash_status("已重新抽選")


def main():
    root = tk.Tk()
    PromptGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
