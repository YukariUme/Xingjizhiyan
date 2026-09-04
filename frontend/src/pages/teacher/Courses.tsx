/** 课程管理：列表 + 新建。 */

import { useState } from "react";
import { api } from "../../api";
import { Card, EmptyState, Loading, Modal, useAsync } from "../../components/ui";
import type { Course, CourseInvitation, User } from "../../types";

export default function TeacherCourses() {
  const { data, loading, setData } = useAsync<Course[]>(() => api.get("/courses"));
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", code: "", description: "", semester: "2026 春季" });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const [manage, setManage] = useState<Course | null>(null);
  const [students, setStudents] = useState<User[]>([]);
  const [candidates, setCandidates] = useState<User[]>([]);
  const [invitations, setInvitations] = useState<CourseInvitation[]>([]);
  const [inviteUsername, setInviteUsername] = useState("");
  const [inviteMsg, setInviteMsg] = useState("");
  const [manageBusy, setManageBusy] = useState(false);

  const create = async () => {
    setErr("");
    setSaving(true);
    try {
      const created = await api.post<Course>("/courses", form);
      setData([...(data ?? []), created]);
      setOpen(false);
      setForm({ name: "", code: "", description: "", semester: "2026 春季" });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "创建失败");
    } finally {
      setSaving(false);
    }
  };

  const openManage = async (c: Course) => {
    setManage(c);
    setInviteUsername("");
    setInviteMsg("");
    setManageBusy(true);
    try {
      const [cur, allStudents, allInvites] = await Promise.all([
        api.get<User[]>(`/courses/${c.id}/students`),
        api.get<User[]>("/auth/students"),
        api.get<CourseInvitation[]>(`/courses/${c.id}/invitations`),
      ]);
      setStudents(cur);
      setInvitations(allInvites);
      const pendingIds = new Set(
        allInvites.filter((i) => i.status === "pending").map((i) => i.student_id)
      );
      setCandidates(
        allStudents.filter(
          (s) =>
            !cur.some((x) => x.id === s.id) &&
            !pendingIds.has(s.id)
        )
      );
    } catch (e) {
      setInviteMsg(e instanceof Error ? e.message : "加载失败");
    } finally {
      setManageBusy(false);
    }
  };

  const invite = async () => {
    if (!manage || !inviteUsername.trim()) return;
    setManageBusy(true);
    setInviteMsg("");
    try {
      const res = await api.post<{ student: User }>(`/courses/${manage.id}/invite`, {
        student_username: inviteUsername.trim(),
      });
      setStudents((cur) => [...cur, res.student]);
      setCandidates((cur) => cur.filter((s) => s.id !== res.student.id));
      setInviteUsername("");
      setInviteMsg(`✓ 已邀请 ${res.student.display_name}`);
      const refreshed = await api.get<CourseInvitation[]>(`/courses/${manage.id}/invitations`);
      setInvitations(refreshed);
    } catch (e) {
      setInviteMsg(e instanceof Error ? e.message : "邀请失败");
    } finally {
      setManageBusy(false);
    }
  };

  const cancelInvite = async (inv: CourseInvitation) => {
    try {
      await api.post(`/course-invitations/${inv.id}/cancel`, {});
      setInvitations((cur) => cur.filter((i) => i.id !== inv.id));
      setCandidates((cur) => [...cur, { id: inv.student_id, username: inv.student_username, display_name: inv.student_name, role: "student", title: "", bio: "" }]);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "撤销失败");
    }
  };

  const remove = async (c: Course) => {
    if (!window.confirm(`确认删除课程「${c.name}」？其选课、作业、题目与提交数据将一并删除且不可恢复。`)) return;
    try {
      await api.delete(`/courses/${c.id}`);
      setData((data ?? []).filter((x) => x.id !== c.id));
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "删除失败");
    }
  };

  if (loading) return <Loading />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>课程管理</h1>
          <p>维护本学期课程与选课学生，作业与学情以课程为单位组织</p>
        </div>
        <button className="btn btn-primary" onClick={() => setOpen(true)}>＋ 新建课程</button>
      </div>

      {!data || data.length === 0 ? (
        <EmptyState text="还没有课程，点击右上角新建" />
      ) : (
        <div className="grid grid-3">
          {data.map((c) => (
            <Card key={c.id} title={c.name} extra={<span className="badge gray">{c.code}</span>}>
              <p className="small" style={{ color: "var(--text-2)", minHeight: 44 }}>{c.description}</p>
              <div className="row wrap">
                <span className="badge">{c.student_count} 名学生</span>
                <span className="badge purple">{c.assignment_count} 份作业</span>
                <span className="badge gray">{c.semester}</span>
                {c.pending_count > 0 && <span className="badge orange">{c.pending_count} 待接受</span>}
              </div>
              <div className="row mt-16">
                <button className="btn btn-sm btn-primary" onClick={() => void openManage(c)}>
                  学生管理
                </button>
                <button className="btn btn-sm btn-danger" onClick={() => void remove(c)}>
                  删除课程
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal
        title="新建课程"
        open={open}
        onClose={() => setOpen(false)}
        footer={
          <>
            <button className="btn" onClick={() => setOpen(false)}>取消</button>
            <button className="btn btn-primary" onClick={() => void create()} disabled={saving || !form.name || !form.code}>
              {saving ? "创建中…" : "创建"}
            </button>
          </>
        }
      >
        <div className="form-grid">
          <div className="field">
            <label>课程名称 *</label>
            <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="如：数据结构" />
          </div>
          <div className="field">
            <label>课程编号 *</label>
            <input className="input" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="如：CS201" />
          </div>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>课程简介</label>
            <textarea className="textarea" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="field">
            <label>学期</label>
            <input className="input" value={form.semester} onChange={(e) => setForm({ ...form, semester: e.target.value })} />
          </div>
        </div>
        {err && <div className="badge red mb-8">{err}</div>}
      </Modal>

      <Modal
        title={`学生管理 · ${manage?.name ?? ""}`}
        open={manage != null}
        onClose={() => setManage(null)}
        footer={<button className="btn" onClick={() => setManage(null)}>关闭</button>}
      >
        {manageBusy ? (
          <Loading />
        ) : (
          <>
            <div className="row mb-8" style={{ gap: 6 }}>
              <input
                className="input grow"
                list="student-candidates"
                placeholder="输入学生用户名邀请（如 student1）"
                value={inviteUsername}
                onChange={(e) => setInviteUsername(e.target.value)}
              />
              <datalist id="student-candidates">
                {candidates.map((s) => (
                  <option key={s.id} value={s.username}>{s.display_name}</option>
                ))}
              </datalist>
              <button className="btn btn-primary" onClick={() => void invite()} disabled={!inviteUsername.trim()}>
                邀请
              </button>
            </div>
            {inviteMsg && <div className="small mb-8" style={{ color: inviteMsg.startsWith("✓") ? "var(--success)" : "var(--danger)" }}>{inviteMsg}</div>}
            <h3>已选学生（{students.length}）</h3>
            {students.length === 0 ? (
              <div className="muted small">还没有学生，输入用户名邀请加入</div>
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr><th>姓名</th><th>用户名</th></tr>
                  </thead>
                  <tbody>
                    {students.map((s) => (
                      <tr key={s.id}>
                        <td><b>{s.display_name}</b></td>
                        <td className="mono">{s.username}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <h3 className="mt-16">待接受邀请（{invitations.filter((i) => i.status === "pending").length}）</h3>
            {invitations.filter((i) => i.status === "pending").length === 0 ? (
              <div className="muted small">暂无待接受邀请</div>
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr><th>学生</th><th>状态</th><th>操作</th></tr>
                  </thead>
                  <tbody>
                    {invitations
                      .filter((i) => i.status === "pending")
                      .map((inv) => (
                        <tr key={inv.id}>
                          <td><b>{inv.student_name}</b><div className="small muted">{inv.student_username}</div></td>
                          <td><span className="badge orange">待学生接受</span></td>
                          <td>
                            <button className="btn btn-sm btn-danger" onClick={() => void cancelInvite(inv)}>
                              撤销
                            </button>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </Modal>
    </div>
  );
}
