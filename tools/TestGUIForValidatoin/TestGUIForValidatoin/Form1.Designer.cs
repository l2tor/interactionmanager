namespace TestGUIForValidatoin
{
    partial class Form1
    {
        /// <summary>
        /// Erforderliche Designervariable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Verwendete Ressourcen bereinigen.
        /// </summary>
        /// <param name="disposing">True, wenn verwaltete Ressourcen gelöscht werden sollen; andernfalls False.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Vom Windows Form-Designer generierter Code

        /// <summary>
        /// Erforderliche Methode für die Designerunterstützung.
        /// Der Inhalt der Methode darf nicht mit dem Code-Editor geändert werden.
        /// </summary>
        private void InitializeComponent()
        {
            this.btn_vad_start = new System.Windows.Forms.Button();
            this.label1 = new System.Windows.Forms.Label();
            this.txt_IP = new System.Windows.Forms.TextBox();
            this.label2 = new System.Windows.Forms.Label();
            this.btn_connect = new System.Windows.Forms.Button();
            this.btn_disconnect = new System.Windows.Forms.Button();
            this.label3 = new System.Windows.Forms.Label();
            this.btn_obj_selected = new System.Windows.Forms.Button();
            this.label4 = new System.Windows.Forms.Label();
            this.btn_send_sp_rel = new System.Windows.Forms.Button();
            this.ddl_obj_1 = new System.Windows.Forms.ComboBox();
            this.ddl_relation = new System.Windows.Forms.ComboBox();
            this.ddl_obj_2 = new System.Windows.Forms.ComboBox();
            this.label5 = new System.Windows.Forms.Label();
            this.label6 = new System.Windows.Forms.Label();
            this.label7 = new System.Windows.Forms.Label();
            this.ddl_selected_object = new System.Windows.Forms.ComboBox();
            this.btn_load_scene = new System.Windows.Forms.Button();
            this.SuspendLayout();
            // 
            // btn_vad_start
            // 
            this.btn_vad_start.Location = new System.Drawing.Point(60, 22);
            this.btn_vad_start.Margin = new System.Windows.Forms.Padding(2, 2, 2, 2);
            this.btn_vad_start.Name = "btn_vad_start";
            this.btn_vad_start.Size = new System.Drawing.Size(50, 24);
            this.btn_vad_start.TabIndex = 0;
            this.btn_vad_start.Text = "Send";
            this.btn_vad_start.UseVisualStyleBackColor = true;
            this.btn_vad_start.Click += new System.EventHandler(this.btn_vad_send_Click);
            // 
            // label1
            // 
            this.label1.AutoSize = true;
            this.label1.Location = new System.Drawing.Point(16, 27);
            this.label1.Margin = new System.Windows.Forms.Padding(2, 0, 2, 0);
            this.label1.Name = "label1";
            this.label1.Size = new System.Drawing.Size(29, 13);
            this.label1.TabIndex = 1;
            this.label1.Text = "VAD";
            // 
            // txt_IP
            // 
            this.txt_IP.Location = new System.Drawing.Point(43, 432);
            this.txt_IP.Margin = new System.Windows.Forms.Padding(2, 2, 2, 2);
            this.txt_IP.Name = "txt_IP";
            this.txt_IP.Size = new System.Drawing.Size(114, 20);
            this.txt_IP.TabIndex = 2;
            this.txt_IP.Text = "127.0.0.1";
            // 
            // label2
            // 
            this.label2.AutoSize = true;
            this.label2.Location = new System.Drawing.Point(8, 434);
            this.label2.Margin = new System.Windows.Forms.Padding(2, 0, 2, 0);
            this.label2.Name = "label2";
            this.label2.Size = new System.Drawing.Size(17, 13);
            this.label2.TabIndex = 3;
            this.label2.Text = "IP";
            // 
            // btn_connect
            // 
            this.btn_connect.Location = new System.Drawing.Point(173, 429);
            this.btn_connect.Margin = new System.Windows.Forms.Padding(2, 2, 2, 2);
            this.btn_connect.Name = "btn_connect";
            this.btn_connect.Size = new System.Drawing.Size(67, 24);
            this.btn_connect.TabIndex = 4;
            this.btn_connect.Text = "Connect";
            this.btn_connect.UseVisualStyleBackColor = true;
            this.btn_connect.Click += new System.EventHandler(this.btn_connect_Click);
            // 
            // btn_disconnect
            // 
            this.btn_disconnect.Enabled = false;
            this.btn_disconnect.Location = new System.Drawing.Point(251, 429);
            this.btn_disconnect.Margin = new System.Windows.Forms.Padding(2, 2, 2, 2);
            this.btn_disconnect.Name = "btn_disconnect";
            this.btn_disconnect.Size = new System.Drawing.Size(67, 24);
            this.btn_disconnect.TabIndex = 5;
            this.btn_disconnect.Text = "Disconnect";
            this.btn_disconnect.UseVisualStyleBackColor = true;
            this.btn_disconnect.Click += new System.EventHandler(this.btn_disconnect_Click);
            // 
            // label3
            // 
            this.label3.AutoSize = true;
            this.label3.Location = new System.Drawing.Point(16, 62);
            this.label3.Margin = new System.Windows.Forms.Padding(2, 0, 2, 0);
            this.label3.Name = "label3";
            this.label3.Size = new System.Drawing.Size(85, 13);
            this.label3.TabIndex = 7;
            this.label3.Text = "Select Object ID";
            // 
            // btn_obj_selected
            // 
            this.btn_obj_selected.Location = new System.Drawing.Point(143, 74);
            this.btn_obj_selected.Margin = new System.Windows.Forms.Padding(2, 2, 2, 2);
            this.btn_obj_selected.Name = "btn_obj_selected";
            this.btn_obj_selected.Size = new System.Drawing.Size(50, 24);
            this.btn_obj_selected.TabIndex = 6;
            this.btn_obj_selected.Text = "Send";
            this.btn_obj_selected.UseVisualStyleBackColor = true;
            this.btn_obj_selected.Click += new System.EventHandler(this.btn_obj_selected_Click);
            // 
            // label4
            // 
            this.label4.AutoSize = true;
            this.label4.Location = new System.Drawing.Point(16, 107);
            this.label4.Margin = new System.Windows.Forms.Padding(2, 0, 2, 0);
            this.label4.Name = "label4";
            this.label4.Size = new System.Drawing.Size(81, 13);
            this.label4.TabIndex = 10;
            this.label4.Text = "Spatial Realtion";
            // 
            // btn_send_sp_rel
            // 
            this.btn_send_sp_rel.Location = new System.Drawing.Point(334, 138);
            this.btn_send_sp_rel.Margin = new System.Windows.Forms.Padding(2, 2, 2, 2);
            this.btn_send_sp_rel.Name = "btn_send_sp_rel";
            this.btn_send_sp_rel.Size = new System.Drawing.Size(50, 24);
            this.btn_send_sp_rel.TabIndex = 9;
            this.btn_send_sp_rel.Text = "Send";
            this.btn_send_sp_rel.UseVisualStyleBackColor = true;
            this.btn_send_sp_rel.Click += new System.EventHandler(this.btn_send_sp_rel_Click);
            // 
            // ddl_obj_1
            // 
            this.ddl_obj_1.FormattingEnabled = true;
            this.ddl_obj_1.Items.AddRange(new object[] {
            "m_elephant_1",
            "m_elephant_2",
            "s_cage_1",
            "m_monkey_1",
            "m_giraffe_1",
            "m_giraffe_2",
            "m_giraffe_3",
            "s_cage_2",
            "s_cage_3",
            "m_tree_1",
            "m_tree_2",
            "m_tree_3"});
            this.ddl_obj_1.Location = new System.Drawing.Point(19, 141);
            this.ddl_obj_1.Margin = new System.Windows.Forms.Padding(2, 2, 2, 2);
            this.ddl_obj_1.Name = "ddl_obj_1";
            this.ddl_obj_1.Size = new System.Drawing.Size(103, 21);
            this.ddl_obj_1.TabIndex = 11;
            // 
            // ddl_relation
            // 
            this.ddl_relation.FormattingEnabled = true;
            this.ddl_relation.Items.AddRange(new object[] {
            "in"});
            this.ddl_relation.Location = new System.Drawing.Point(125, 141);
            this.ddl_relation.Margin = new System.Windows.Forms.Padding(2, 2, 2, 2);
            this.ddl_relation.Name = "ddl_relation";
            this.ddl_relation.Size = new System.Drawing.Size(82, 21);
            this.ddl_relation.TabIndex = 12;
            // 
            // ddl_obj_2
            // 
            this.ddl_obj_2.FormattingEnabled = true;
            this.ddl_obj_2.Items.AddRange(new object[] {
            "m_elephant_1",
            "m_elephant_2",
            "s_cage_1",
            "m_monkey_1",
            "m_giraffe_1",
            "m_giraffe_2",
            "m_giraffe_3",
            "s_cage_2",
            "s_cage_3",
            "s_lake_1"});
            this.ddl_obj_2.Location = new System.Drawing.Point(227, 141);
            this.ddl_obj_2.Margin = new System.Windows.Forms.Padding(2, 2, 2, 2);
            this.ddl_obj_2.Name = "ddl_obj_2";
            this.ddl_obj_2.Size = new System.Drawing.Size(105, 21);
            this.ddl_obj_2.TabIndex = 13;
            // 
            // label5
            // 
            this.label5.AutoSize = true;
            this.label5.Location = new System.Drawing.Point(16, 126);
            this.label5.Margin = new System.Windows.Forms.Padding(2, 0, 2, 0);
            this.label5.Name = "label5";
            this.label5.Size = new System.Drawing.Size(35, 13);
            this.label5.TabIndex = 14;
            this.label5.Text = "Obj_1";
            // 
            // label6
            // 
            this.label6.AutoSize = true;
            this.label6.Location = new System.Drawing.Point(224, 126);
            this.label6.Margin = new System.Windows.Forms.Padding(2, 0, 2, 0);
            this.label6.Name = "label6";
            this.label6.Size = new System.Drawing.Size(35, 13);
            this.label6.TabIndex = 15;
            this.label6.Text = "Obj_2";
            // 
            // label7
            // 
            this.label7.AutoSize = true;
            this.label7.Location = new System.Drawing.Point(122, 126);
            this.label7.Margin = new System.Windows.Forms.Padding(2, 0, 2, 0);
            this.label7.Name = "label7";
            this.label7.Size = new System.Drawing.Size(46, 13);
            this.label7.TabIndex = 16;
            this.label7.Text = "Relation";
            // 
            // ddl_selected_object
            // 
            this.ddl_selected_object.FormattingEnabled = true;
            this.ddl_selected_object.Items.AddRange(new object[] {
            "m_elephant_1",
            "m_elephant_2",
            "s_cage_1",
            "m_monkey_1",
            "m_giraffe_1",
            "m_giraffe_2",
            "m_giraffe_3",
            "s_cage_2",
            "s_cage_3",
            "zoo"});
            this.ddl_selected_object.Location = new System.Drawing.Point(19, 74);
            this.ddl_selected_object.Margin = new System.Windows.Forms.Padding(2, 2, 2, 2);
            this.ddl_selected_object.Name = "ddl_selected_object";
            this.ddl_selected_object.Size = new System.Drawing.Size(103, 21);
            this.ddl_selected_object.TabIndex = 17;
            // 
            // btn_load_scene
            // 
            this.btn_load_scene.Location = new System.Drawing.Point(303, 195);
            this.btn_load_scene.Margin = new System.Windows.Forms.Padding(2, 2, 2, 2);
            this.btn_load_scene.Name = "btn_load_scene";
            this.btn_load_scene.Size = new System.Drawing.Size(81, 24);
            this.btn_load_scene.TabIndex = 18;
            this.btn_load_scene.Text = "Load Scene";
            this.btn_load_scene.UseVisualStyleBackColor = true;
            this.btn_load_scene.Click += new System.EventHandler(this.btn_load_scene_Click);
            // 
            // Form1
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(410, 486);
            this.Controls.Add(this.btn_load_scene);
            this.Controls.Add(this.ddl_selected_object);
            this.Controls.Add(this.label7);
            this.Controls.Add(this.label6);
            this.Controls.Add(this.label5);
            this.Controls.Add(this.ddl_obj_2);
            this.Controls.Add(this.ddl_relation);
            this.Controls.Add(this.ddl_obj_1);
            this.Controls.Add(this.label4);
            this.Controls.Add(this.btn_send_sp_rel);
            this.Controls.Add(this.label3);
            this.Controls.Add(this.btn_obj_selected);
            this.Controls.Add(this.btn_disconnect);
            this.Controls.Add(this.btn_connect);
            this.Controls.Add(this.label2);
            this.Controls.Add(this.txt_IP);
            this.Controls.Add(this.label1);
            this.Controls.Add(this.btn_vad_start);
            this.Margin = new System.Windows.Forms.Padding(2, 2, 2, 2);
            this.Name = "Form1";
            this.Text = "Form1";
            this.Load += new System.EventHandler(this.Form1_Load);
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.Windows.Forms.Button btn_vad_start;
        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.TextBox txt_IP;
        private System.Windows.Forms.Label label2;
        private System.Windows.Forms.Button btn_connect;
        private System.Windows.Forms.Button btn_disconnect;
        private System.Windows.Forms.Label label3;
        private System.Windows.Forms.Button btn_obj_selected;
        private System.Windows.Forms.Label label4;
        private System.Windows.Forms.Button btn_send_sp_rel;
        private System.Windows.Forms.ComboBox ddl_obj_1;
        private System.Windows.Forms.ComboBox ddl_relation;
        private System.Windows.Forms.ComboBox ddl_obj_2;
        private System.Windows.Forms.Label label5;
        private System.Windows.Forms.Label label6;
        private System.Windows.Forms.Label label7;
        private System.Windows.Forms.ComboBox ddl_selected_object;
        private System.Windows.Forms.Button btn_load_scene;
    }
}

