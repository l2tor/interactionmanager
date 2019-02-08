using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace TestGUIForValidatoin
{
    public partial class Form1 : Form
    {

        private AsynchronousClient client;
        public Form1()
        {
            InitializeComponent();
        }

        private void Form1_Load(object sender, EventArgs e) {
            client = new AsynchronousClient(); //client for TCP connection
            ddl_obj_1.SelectedIndex = 0;
            ddl_obj_2.SelectedIndex = 0;
            ddl_relation.SelectedIndex = 0;
        }

        private void btn_vad_send_Click(object sender, EventArgs e)
        {
            client.Send("call:tablet.interactionmanager.vadStop");
        }

        private void btn_connect_Click(object sender, EventArgs e)
        {
            client.StartClient(System.Net.IPAddress.Parse(txt_IP.Text), this);
            if (client.bConnected == true)
            {
                //register the client
                System.Threading.Thread.Sleep(1000);
                client.Send("register:TestGUI");
                btn_connect.Enabled = false;
                btn_disconnect.Enabled = true;
            }
        }

        private void btn_disconnect_Click(object sender, EventArgs e)
        {
            if (client.bConnected == true)
            {
                client.CloseSocket();
                btn_connect.Enabled = true;
                btn_disconnect.Enabled = false;
            }
        }

        private void btn_obj_selected_Click(object sender, EventArgs e)
        {
            client.Send("call:tablet.interactionmanager.touchDown|{\"id\": \"" + ddl_selected_object.SelectedItem.ToString() + "\", \"x\":10, \"y\":10}");
            System.Threading.Thread.Sleep(1000);
            client.Send("call:tablet.interactionmanager.touchUp|{\"id\": \"" + ddl_selected_object.SelectedItem.ToString() + "\", \"x\":100, \"y\":100}");
        }

        private void btn_send_sp_rel_Click(object sender, EventArgs e)
        {
            client.Send("call:tablet.interactionmanager.updtSpRel|{\"" + ddl_obj_1.SelectedItem.ToString() + "\": [{\"obj_2\":\"" + ddl_obj_2.SelectedItem.ToString() + "\", \"relation\":\"" + ddl_relation.SelectedItem.ToString() + "\"}]}");
        }

        private void btn_load_scene_Click(object sender, EventArgs e)
        {
            string[] lines = System.IO.File.ReadAllLines(@"../../data/zoo_1.json");
            string result = "";
            foreach (String line in lines) {
                result += line.Trim();
            }
            client.Send("call:tablet.WebSocket.loadScene|" + result);
        }
    }
}
