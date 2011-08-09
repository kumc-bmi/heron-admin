/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */
package edu.kumc.informatics.heron.servlet;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.Charset;
import java.util.Map;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.springframework.core.io.Resource;
import org.springframework.web.servlet.view.InternalResourceView;
import org.antlr.stringtemplate.AutoIndentWriter;
import org.antlr.stringtemplate.StringTemplate;
import org.antlr.stringtemplate.language.DefaultTemplateLexer;

/**
 *
 * @author connolly
 * Ack: Nick Carroll
 * http://ca.rroll.net/2009/06/18/using-stringtemplate-as-the-view-engine-for-your-spring-mvc-application/
 * http://stackoverflow.com/questions/488930/which-java-mvc-frameworks-integrate-easily-with-stringtemplate 
 */
public class StringTemplateView extends InternalResourceView {

    @Override
    protected void renderMergedOutputModel(Map model, HttpServletRequest request,
                HttpServletResponse response) throws IOException {

        Resource templateResource = getApplicationContext().getResource(getUrl());
        String templateContent = readStreamUTF8(templateResource.getInputStream());        
        StringTemplate template = new StringTemplate(templateContent, DefaultTemplateLexer.class);

        template.setAttributes(model);

        template.write(new AutoIndentWriter(response.getWriter()));
    }

    /**
     * ack: http://stackoverflow.com/questions/326390/how-to-create-a-java-string-from-the-contents-of-a-file/326440
     */
    private static String readStreamUTF8(InputStream stream) throws IOException {
        try {
            Reader reader = new BufferedReader(new InputStreamReader(stream, utf8));
            StringBuilder builder = new StringBuilder();
            char[] buffer = new char[8192];
            int read;
            while ((read = reader.read(buffer, 0, buffer.length)) > 0) {
                builder.append(buffer, 0, read);
            }
            return builder.toString();
        }
        finally {
            stream.close();
        }
    }
    private static final Charset utf8 = Charset.forName("UTF-8");
}
