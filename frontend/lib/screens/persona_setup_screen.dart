import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:image_picker/image_picker.dart';
import 'package:file_picker/file_picker.dart';
import '../main.dart';
import '../services/api_service.dart';

/// 人格创建向导 — Upload chat logs, photos, configure personality.
class PersonaSetupScreen extends StatefulWidget {
  final int? personaId;
  const PersonaSetupScreen({super.key, this.personaId});

  @override
  State<PersonaSetupScreen> createState() => _PersonaSetupScreenState();
}

class _PersonaSetupScreenState extends State<PersonaSetupScreen> {
  final _formKey = GlobalKey<FormState>();
  int _step = 0;
  bool _loading = false;

  // Form fields
  final _nameCtrl = TextEditingController();
  final _nicknameCtrl = TextEditingController();
  final _speakingCtrl = TextEditingController();
  final _customPromptCtrl = TextEditingController();
  final _relationshipCtrl = TextEditingController();
  String _gender = 'unspecified';
  String _emotion = 'warm,friendly';
  final List<String> _habits = [];
  final List<String> _hobbies = [];
  String? _chatFilePath;
  int _importedCount = 0;

  @override
  void dispose() {
    _nameCtrl.dispose(); _nicknameCtrl.dispose();
    _speakingCtrl.dispose(); _customPromptCtrl.dispose();
    _relationshipCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickChatFile() async {
    final result = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: ['txt', 'json']);
    if (result != null) {
      setState(() => _chatFilePath = result.files.single.path);
      if (widget.personaId != null) {
        final api = context.read<AppState>().api;
        try {
          final res = await api.uploadChatFile(widget.personaId!, _chatFilePath!);
          setState(() => _importedCount = res['imported'] ?? 0);
        } catch (e) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('上传失败: $e')));
        }
      }
    }
  }

  Future<void> _pickPhoto() async {
    final picker = ImagePicker();
    final image = await picker.pickImage(source: ImageSource.gallery);
    if (image != null && widget.personaId != null) {
      final api = context.read<AppState>().api;
      // Upload photo via multipart
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('照片已选择')));
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    final api = context.read<AppState>().api;

    final data = {
      'name': _nameCtrl.text,
      'nickname': _nicknameCtrl.text,
      'gender': _gender,
      'speaking_style': _speakingCtrl.text,
      'habits': _habits,
      'hobbies': _hobbies,
      'custom_prompt': _customPromptCtrl.text,
      'emotion_range': _emotion,
      'relationship_context': _relationshipCtrl.text,
    };

    try {
      if (widget.personaId != null) {
        await api.updatePersona(widget.personaId!, data);
      } else {
        final res = await api.createPersona(data);
        final id = res['id'];
        if (_chatFilePath != null) {
          await api.uploadChatFile(id, _chatFilePath!);
        }
      }
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('保存失败: $e')));
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.personaId != null ? '调整人格' : '创建人格')),
      body: Form(
        key: _formKey,
        child: Stepper(
          currentStep: _step,
          onStepContinue: () => _step < 4 ? setState(() => _step++) : _submit(),
          onStepCancel: () => _step > 0 ? setState(() => _step--) : null,
          controlsBuilder: (ctx, details) => Row(
            children: [
              if (_step < 4)
                ElevatedButton(onPressed: details.onStepContinue, child: const Text('下一步')),
              if (_step > 0)
                TextButton(onPressed: details.onStepCancel, child: const Text('返回')),
              if (_step == 4)
                ElevatedButton(
                  onPressed: _loading ? null : _submit,
                  child: _loading ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('完成创建'),
                ),
            ],
          ),
          steps: [
            // Step 0: Upload Chat Records
            Step(
              title: const Text('📤 导入聊天记录'),
              subtitle: Text(_importedCount > 0 ? '已导入 $_importedCount 条消息' : '上传微信/QQ导出文件'),
              content: Column(
                children: [
                  OutlinedButton.icon(
                    onPressed: _pickChatFile,
                    icon: const Icon(Icons.upload_file),
                    label: const Text('选择聊天记录文件 (.txt / .json)'),
                  ),
                  const SizedBox(height: 12),
                  const Text('支持微信导出、QQ导出、JSON格式', style: TextStyle(color: Colors.grey, fontSize: 12)),
                ],
              ),
              isActive: _step >= 0,
            ),
            // Step 1: Basic Info
            Step(
              title: const Text('👤 基本信息'),
              content: Column(
                children: [
                  TextFormField(controller: _nameCtrl, decoration: const InputDecoration(labelText: 'TA的名字 *'), validator: (v) => v!.isEmpty ? '必填' : null),
                  const SizedBox(height: 12),
                  TextFormField(controller: _nicknameCtrl, decoration: const InputDecoration(labelText: '昵称')),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    value: _gender,
                    items: const [
                      DropdownMenuItem(value: 'unspecified', child: Text('不指定')),
                      DropdownMenuItem(value: 'male', child: Text('男')),
                      DropdownMenuItem(value: 'female', child: Text('女')),
                    ],
                    onChanged: (v) => setState(() => _gender = v!),
                    decoration: const InputDecoration(labelText: '性别'),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(controller: _relationshipCtrl, decoration: const InputDecoration(labelText: '你们的关系', hintText: '如：大学同学、暗恋对象')),
                ],
              ),
              isActive: _step >= 1,
            ),
            // Step 2: Speaking Style
            Step(
              title: const Text('💬 说话风格'),
              content: Column(
                children: [
                  TextFormField(controller: _speakingCtrl, maxLines: 3, decoration: const InputDecoration(labelText: '说话风格描述', hintText: '语气温柔、喜欢用省略号、偶尔毒舌...')),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    value: _emotion,
                    items: const [
                      DropdownMenuItem(value: 'warm,friendly', child: Text('温暖友好 🥰')),
                      DropdownMenuItem(value: 'humorous,witty', child: Text('幽默风趣 😄')),
                      DropdownMenuItem(value: 'cool,aloof', child: Text('高冷淡漠 😎')),
                      DropdownMenuItem(value: 'sweet,clingy', child: Text('甜腻粘人 🍯')),
                      DropdownMenuItem(value: 'tsundere', child: Text('傲娇 😤')),
                    ],
                    onChanged: (v) => setState(() => _emotion = v!),
                    decoration: const InputDecoration(labelText: '情感倾向'),
                  ),
                ],
              ),
              isActive: _step >= 2,
            ),
            // Step 3: Habits
            Step(
              title: const Text('🎯 习惯 & 爱好'),
              content: Column(
                children: [
                  _buildTagInput('聊天习惯', _habits, hint: '如：喜欢发猫猫表情包、深夜感性'),
                  const SizedBox(height: 12),
                  _buildTagInput('兴趣爱好', _hobbies, hint: '如：打游戏、看电影、健身'),
                ],
              ),
              isActive: _step >= 3,
            ),
            // Step 4: Custom Prompt
            Step(
              title: const Text('📝 补充说明'),
              content: TextFormField(
                controller: _customPromptCtrl,
                maxLines: 5,
                decoration: const InputDecoration(
                  labelText: '还有什么要补充的？',
                  hintText: '如：TA是个程序员，戴眼镜，平时话不多但熟了话很多。喜欢吃辣但是一吃就拉肚子...',
                ),
              ),
              isActive: _step >= 4,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTagInput(String label, List<String> tags, {String hint = ''}) {
    final ctrl = TextEditingController();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: ctrl,
                decoration: InputDecoration(hintText: hint, isDense: true),
                onSubmitted: (v) {
                  if (v.isNotEmpty) { setState(() => tags.add(v)); ctrl.clear(); }
                },
              ),
            ),
            IconButton(icon: const Icon(Icons.add_circle), onPressed: () {
              if (ctrl.text.isNotEmpty) { setState(() => tags.add(ctrl.text)); ctrl.clear(); }
            }),
          ],
        ),
        if (tags.isNotEmpty)
          Wrap(
            spacing: 6, runSpacing: 4,
            children: tags.map((t) => Chip(
              label: Text(t, style: const TextStyle(fontSize: 12)),
              deleteIcon: const Icon(Icons.close, size: 16),
              onDeleted: () => setState(() => tags.remove(t)),
            )).toList(),
          ),
      ],
    );
  }
}
